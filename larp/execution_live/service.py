"""Proposed I3 command mapping and I4 broadcast observations; no unfenced store fallback.

The service only drives an injected W04 Executor. The existing Executor still rejects live
bundles pending verified decoder, production store, manifest and logging integration.
"""
from larp.execution import Blocked, Intent, USDT, NATIVE_BNB, integer
from larp.marketdata.port import TOKENS


def map_command(command, *, run_id, wallet, version_id, router, token_decimals, limits, now_ms):
    if hasattr(command,'read'):command=command.read()
    if command.get('kind')!='EXECUTION_REQUEST':raise Blocked('unsupported command kind')
    p=command['payload']
    for k in ('intent_id','decision_id','expires_ms'):
        if p.get(k)!=command.get('command_id' if k=='intent_id' else k):
            raise Blocked('command/payload identity mismatch')
    if integer(command['expires_ms'],positive=True)<=integer(now_ms):raise Blocked('expired execution command')
    kind=p.get('kind','BSTOCK_TRADE');symbol=p['symbol'];side=p['side']
    if kind=='GAS_TOP_UP':
        if symbol!='BNB' or side!='BUY':raise Blocked('gas top-up must buy native BNB')
        token=NATIVE_BNB;decimals=18
    else:
        if kind!='BSTOCK_TRADE' or symbol not in TOKENS or side not in ('BUY','SELL'):
            raise Blocked('unsupported economic action')
        token=TOKENS[symbol];decimals=integer(token_decimals[symbol])
    pay,receive=(USDT,token) if side=='BUY' else (token,USDT)
    expected_pay='USDT' if side=='BUY' else symbol
    if p.get('amount_kind')!='EXACT_IN' or p.get('pay_asset')!=expected_pay:
        raise Blocked('only bound exact-in commands accepted')
    # Planner money scale is 10^6; BSC USDT units are 10^18. Never pass 40e6 as chain input.
    amount=integer(p['pay_units'],positive=True)*(10**12 if side=='BUY' else 1)
    receive_decimals=decimals if side=='BUY' else 6
    if p.get('receive_decimals')!=receive_decimals:raise Blocked('receive scale mismatch')
    minimum=integer(p['min_receive_units'],positive=True)*(1 if side=='BUY' else 10**12)
    result=Intent(run_id,command['round_id'],command['decision_id'],p['intent_id'],version_id,p['intent_id'],
                  wallet.lower(),pay,receive,amount,minimum,router.lower(),command['expires_ms']//1000,
                  integer(limits['max_gas'],positive=True),integer(limits['max_gas_price'],positive=True),
                  integer(limits['gas_budget'],positive=True),kind=kind)
    result.validate()
    return result


def broadcast_observation(state,attempt):
    if not attempt.tx_hash or attempt.broadcast_at is None:raise Blocked('no durable broadcast attempt')
    intent=state.intent
    return dict(schema='ExecutionObservation.v1',kind='BROADCAST_ATTEMPTED',settlement='UNKNOWN',
                run_id=intent.run_id,wallet_id=intent.wallet,round_id=intent.round_id,intent_id=intent.intent_id,
                event_id=attempt.attempt_id+':broadcast',attempt_id=attempt.attempt_id,tx_hash=attempt.tx_hash,
                decision_id=intent.decision_id,version_id=intent.version_id)


class ExecutionService:
    def __init__(self,*,store,executor,mapping,observe):
        self.store,self.executor,self.mapping,self.observe=store,executor,mapping,observe
    def create_from_command(self,run_id,command_id,epoch,now_ms):
        command=self.store.command(run_id,command_id,epoch,now_ms)
        intent=map_command(command,run_id=run_id,now_ms=now_ms,**self.mapping)
        return self.executor.create(intent,now_ms//1000)
    def advance(self,key,now):
        state=self.executor._load(key)
        if state.status!='ACTIVE':return state
        if not state.attempts or state.attempts[-1].state=='FINAL_SUCCESS':return self.executor.prepare(key,now)
        stage=state.attempts[-1].state
        if stage=='PREPARED':return self.executor.authorize(key,now)
        if stage=='AUTHORIZED':return self.executor.sign(key,now)
        if stage=='SIGNED_DURABLE':
            state=self.executor.broadcast(key,now)
            if state.attempts[-1].broadcast_at is not None:
                self.observe(broadcast_observation(state,state.attempts[-1]))
            return state
        return self.executor.reconcile(key,now)
