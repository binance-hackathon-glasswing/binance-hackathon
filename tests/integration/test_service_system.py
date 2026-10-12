"""IDEA-043: actual command, executor, receipt, settlement, audit and replay wiring.

Only venue/chain/signing/EDGAR transports are synthetic. Signatures cannot authorize EVM transactions.
"""
from dataclasses import replace
from datetime import datetime, timezone
from larp.contracts import Document
from larp.execution import Executor, USDT, TERMINAL
from larp.execution_live.service import ExecutionService
from larp.execution_live.settlement import ReceiptFacts
from larp.execution_live.store import ExecutionStore
from larp.integration.runtime import initial_projection, initial_policy_state, RuntimePlanner, StrategyPolicy
from larp.integration.settlement import ExecutionBridge, settle
from larp.integration.replay import replay_live
from larp.audit.delivery import DeliveryWorker
from larp.runtime.fixtures import FakeReceiver
from larp.storage.postgres import doc
from tests.execution_fixtures import FakeVenue, FakeDecoder, WALLET, ROUTER, TOKEN, finalized, BLOCK
from tests.execution.test_postgres_execution import RegistrySigner, ExecutionGuards
from tests.execution.test_settlement import log
from tests.integration import test_evidence_pipeline as pipeline


class TinyVenue(FakeVenue):
    def __init__(self,store):
        super().__init__(store); self.estimate=1000
    def quote(self,i,nonce): return replace(super().quote(i,nonce),gas=1000)
    def approve(self,i,nonce): return replace(super().approve(i,nonce),gas=1000)


class ServiceSystem(pipeline.PipelineHarness):
    def test_command_to_actual_service_receipt_audit_restart_and_replay(self):
        ledger=pipeline.pipeline_ledger()
        ledger.update(bnb_units=10**15,bnb_decimals=18,bnb_price_units=700000000)
        initial=doc(initial_projection(ledger))
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        self.store.initialize(pipeline.RUN,'fake-wallet',56,initial)
        self.epoch=self.store.takeover(pipeline.RUN,1,offline=True)
        runtime=self.coordinator('MANDATORY_REDUCTION'); runtime.execution=ExecutionBridge()
        self.round(runtime,'r-service','EXSEMI_402_8K')
        record=self.store.load(pipeline.RUN).read()['projection']['round_records']['r-service']
        planned=record['plan']['intents'][0]
        self.assertEqual((planned['side'],planned['mandatory']),('SELL',True))
        registry=ExecutionStore(self.store,run_id=pipeline.RUN,wallet=WALLET)
        guards=ExecutionGuards(registry); venue=TinyVenue(registry)
        executor=Executor(registry,guards,venue,RegistrySigner(registry),FakeDecoder())
        mapping=dict(wallet=WALLET,version_id='integration-fixture',router=ROUTER,
                     token_decimals={'NVDAB':4},limits=dict(max_gas=2000,max_gas_price=1,
                                                         gas_budget=5000,per_trade_cap_units=50000000))
        key=None
        class Chain:
            def receipt(self,tx_hash):
                state=registry.load(key)
                a=next(a for a in state.attempts if a.tx_hash==tx_hash)
                logs=[] if a.step=='APPROVE' else [log(TOKEN,WALLET,ROUTER,state.intent.amount),
                                                     log(USDT,ROUTER,WALLET,state.intent.minimum_output)]
                return dict(finality_verified=True,block_hash=BLOCK,block_number=10,finalized_height=12,
                    tx=dict(hash=tx_hash,nonce=hex(a.payload.nonce),to=a.payload.to,input=a.payload.data,
                            value=hex(a.payload.value),chainId='0x38',gas=hex(a.payload.gas),
                            gasPrice=hex(a.payload.gas_price),**{'from':WALLET}),
                    receipt=dict(transactionHash=tx_hash,blockHash=BLOCK,blockNumber='0xa',gasUsed=hex(500),
                                 effectiveGasPrice='0x1',status='0x1',logs=logs,**{'from':WALLET}))
        facts=ReceiptFacts(Chain(),wallet_id='fake-wallet',valuation=lambda attempt:700000000,
                           registry=registry,epoch=self.epoch,authority_version=self.epoch,
                           round_terminal=lambda state:state.status in TERMINAL and len(record['plan']['intents'])==1)
        def observe(o): runtime.observe(o['event_id'],Document.from_dict(o),settle)
        def service():
            return ExecutionService(store=self.store,executor=executor,mapping=mapping,observe=observe,
                wallet_id='fake-wallet',epoch=self.epoch,authority_version=self.epoch,settlement=facts)
        runner=service(); now=self.w.clock()//1000
        state=runner.create_from_command(pipeline.RUN,planned['intent_id'],self.epoch,now*1000)
        key=state.intent.key
        for tick in range(1,20):
            state=runner.advance(key,now+tick)
            if state.attempts:
                a=state.attempts[-1]
                if a.broadcast_at is not None:
                    venue.outcomes[a.tx_hash]=finalized(a,gas_used=500)
                if a.step=='APPROVE' and a.state=='FINAL_SUCCESS': guards.nonce=a.payload.nonce+1
                if a.step=='SWAP' and a.state=='FINAL_SUCCESS':
                    runner=service()  # restart after durable completion, before publishing final facts
                    runner.advance(key,now+tick+1)
                    break
        self.assertEqual(state.status,'COMPLETED')
        self.assertEqual(len(venue.broadcasts),2)
        current=self.store.load(pipeline.RUN).read()
        self.assertFalse(current['reservations'])
        self.assertEqual(current['projection']['portfolio']['positions']['NVDAB']['units'],0)
        runtime.close('r-service',self.w.clock(),'COMPLETE')
        uploader=DeliveryWorker(self.store,FakeReceiver(),retry_ms=1)
        while uploader.once(pipeline.RUN,self.epoch,self.w.clock()): pass
        self.assertEqual(len(uploader.status(pipeline.RUN)['delivered']),1)
        journal=self.store.journal(pipeline.RUN); expected=self.store.verify(pipeline.RUN)
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        head=replay_live(journal,initial,self.store,builder=runtime.context_builder,run_id=pipeline.RUN,
            wallet_id='fake-wallet',chain_id=56,version_id='integration-fixture',profile_hash=self.h,
            address=WALLET,policy=StrategyPolicy(),planner=RuntimePlanner(job_validity_ms=86400000,job_max_attempts=3),
            execution=ExecutionBridge(),reducer=settle,initial_policy_state=initial_policy_state(pipeline.RUN,self.profile))
        self.assertEqual(head,expected)
