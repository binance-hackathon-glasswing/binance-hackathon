"""Proposed I3 command mapping and I4 broadcast observations; no unfenced store fallback.

The service only drives an injected W04 Executor. The existing Executor still rejects live
bundles pending verified decoder, production store, manifest and logging integration.
"""
from datetime import datetime, timezone

from larp.execution import Blocked, Intent, USDT, NATIVE_BNB, integer, possibly_submitted
from larp.marketdata.port import TOKENS


def map_command(command, *, run_id, wallet, version_id, router, token_decimals, limits, now_ms,
                native_settlement=False):
    """I3 command -> W04 Intent. A GAS_TOP_UP is mapped only when `native_settlement` is True: its fill settles only
    through the transaction-bound native trace (`ChainEvidence.native_receipt`, config `native_trace`), so without it
    the swap's USDT would leave the wallet with no I4 fact to release its reservations (#30, IDEA-061)."""
    try:
        if hasattr(command, 'read'):
            command = command.read()
        if command.get('kind') != 'EXECUTION_REQUEST':
            raise Blocked('unsupported command kind')
        p = command['payload']
        for key in ('intent_id', 'decision_id', 'expires_ms'):
            if p[key] != command['command_id' if key == 'intent_id' else key]:
                raise Blocked('command/payload identity mismatch')
        if integer(command['expires_ms'], positive=True) <= integer(now_ms):
            raise Blocked('expired execution command')
        kind, symbol, side = p.get('kind', 'BSTOCK_TRADE'), p['symbol'], p['side']
        if kind == 'GAS_TOP_UP':
            if symbol != 'BNB' or side != 'BUY':
                raise Blocked('gas top-up must buy native BNB')
            if native_settlement is not True:
                raise Blocked('gas top-up needs native settlement (native_trace) to settle its fill')
            token = NATIVE_BNB
            receive_scale = integer(p['receive_decimals'])
            if receive_scale > 18 or p.get('decimals', receive_scale) != receive_scale:
                raise Blocked('unsupported BNB accounting scale')
            minimum_factor = 10 ** (18 - receive_scale)
        else:
            if kind != 'BSTOCK_TRADE' or symbol not in TOKENS or side not in ('BUY', 'SELL'):
                raise Blocked('unsupported economic action')
            token = TOKENS[symbol]
            receive_scale = integer(token_decimals[symbol]) if side == 'BUY' else 6
            if p['receive_decimals'] != receive_scale:
                raise Blocked('receive scale mismatch')
            minimum_factor = 1 if side == 'BUY' else 10**12
        if p['amount_kind'] != 'EXACT_IN' or p['pay_asset'] != ('USDT' if side == 'BUY' else symbol):
            raise Blocked('only bound exact-in commands accepted')
        cap = integer(limits['per_trade_cap_units'], positive=True)
        cash = integer(p['cash_units'], positive=True)
        fee = integer(p.get('fee_units', 0))
        pay_units = integer(p['pay_units'], positive=True)
        if cash + fee > cap or (side == 'BUY' and cash != pay_units):
            raise Blocked('execution command exceeds per-trade cap or pay amount')
        result = Intent(run_id, command['round_id'], command['decision_id'], p['intent_id'], version_id,
                        p['intent_id'], wallet.lower(), USDT if side == 'BUY' else token,
                        token if side == 'BUY' else USDT, pay_units * (10**12 if side == 'BUY' else 1),
                        integer(p['min_receive_units'], positive=True) * minimum_factor,
                        router.lower(), command['expires_ms'] // 1000,
                        integer(limits['max_gas'], positive=True), integer(limits['max_gas_price'], positive=True),
                        integer(limits['gas_budget'], positive=True), kind=kind, max_cash_units=cap,
                        max_slippage_bps=limits.get('slippage_bps', 50),
                        # #27 Option A: the margin fixed with the plan's authority, never the current profile's
                        authority_margin=integer(p['authority']['margin_seconds'], positive=True)
                        if 'authority' in p else 0)
        result.validate()
        return result
    except (KeyError, TypeError, ValueError, AttributeError):
        raise Blocked('execution command schema rejected') from None


def broadcast_observation(state,attempt,*,wallet_id):
    if not wallet_id:raise Blocked('configured wallet identity required')
    if not attempt.tx_hash or attempt.broadcast_at is None:raise Blocked('no durable broadcast attempt')
    intent=state.intent
    return dict(schema='ExecutionObservation.v1',kind='BROADCAST_ATTEMPTED',
                run_id=intent.run_id,wallet_id=wallet_id,round_id=intent.round_id,intent_id=intent.intent_id,
                event_id=attempt.attempt_id+':broadcast',attempt_id=attempt.attempt_id,tx_hash=attempt.tx_hash,
                decision_id=intent.decision_id,version_id=intent.version_id,step=attempt.step.lower(),
                observed_at=datetime.fromtimestamp(attempt.broadcast_at, timezone.utc).isoformat())


class ExecutionService:
    def __init__(self,*,store,executor,mapping,observe,wallet_id,epoch,authority_version,settlement=None,
                 round_terminal=None,admission=None):
        self.store,self.executor,self.mapping,self.observe=store,executor,mapping,observe
        if not wallet_id:raise Blocked('configured wallet identity required')
        self.wallet_id=wallet_id
        self.settlement=settlement
        self.round_terminal = round_terminal or (lambda state: False)
        self.admission = admission
        self.epoch, self.authority_version = epoch, authority_version
    def create_from_command(self,run_id,command_id,epoch,now_ms):
        if epoch != self.epoch:raise Blocked('command caller ownership mismatch')
        self.executor.store.check_authority(self.epoch, self.authority_version)
        command=self.store.command(run_id,command_id,epoch,now_ms)
        intent=map_command(command,run_id=run_id,now_ms=now_ms,**self.mapping)
        return self.executor.create(intent,now_ms//1000)
    def advance(self,key,now):
        integer(now)
        self.executor.store.check_authority(self.epoch, self.authority_version)
        state=self.executor._load(key)
        # Retry publishing persisted possible-send facts after a crash between
        # the execution commit and observation publication. Consumer dedups event ID.
        for attempt in state.attempts:
            if possibly_submitted(attempt) and attempt.state != 'REJECTED':
                # A rejected send is logged only if the chain later shows it (reconcile then leaves REJECTED).
                self.observe(broadcast_observation(state,attempt,wallet_id=self.wallet_id))
            if attempt.state in ('FINAL_SUCCESS','FINAL_REVERT'):
                if self.settlement is None:
                    raise Blocked('final receipt observation adapter required before advancing')
                fact=self.settlement(state,attempt)
                if (fact.get('schema')!='ExecutionObservation.v1' or fact.get('settlement')!='FINAL'
                        or fact.get('kind') not in ('APPROVAL','FILL','REVERT')
                        or fact.get('intent_id')!=state.intent.intent_id
                        or fact.get('attempt_id')!=attempt.attempt_id or fact.get('tx_hash')!=attempt.tx_hash):
                    raise Blocked('settlement fact identity mismatch')
                self.observe(fact)
        if state.status == 'ABORTED' and not any(a.step == 'SWAP' and possibly_submitted(a)
                                                 for a in state.attempts):
            identity = state.intent.key+':not-submitted'
            rejected = any(a.state == 'NOT_SUBMITTED' for a in state.attempts)
            fact = self.executor.store.lookup_observation(identity)
            if fact is None:
                fact = dict(schema='ExecutionObservation.v1', origin='EXECUTION_RECONCILER',
                kind='NOT_SUBMITTED', settlement='FINAL', run_id=state.intent.run_id, wallet_id=self.wallet_id,
                round_id=state.intent.round_id, intent_id=state.intent.intent_id,
                event_id=identity, observed_at=datetime.fromtimestamp(
                    state.last_observed_at, timezone.utc).isoformat(), intent_terminal=True,
                round_terminal=self.round_terminal(state),
                reason='BROADCAST_REJECTED' if rejected else 'ABORTED_BEFORE_SWAP_BROADCAST')
                fact = self.executor.store.put_observation(fact, self.epoch, self.authority_version)
            self.observe(fact)
        if state.status!='ACTIVE':return state
        if self.admission is not None and not self.admission(state.intent, now):
            # A delayed S1 command cannot sign/send outside its recorded session.
            # Revoke only positive unbroadcast authority; pending/unknown sends
            # still reconcile and publish receipts even after the window ends.
            last = state.attempts[-1] if state.attempts else None
            if last is None or last.state in ('PREPARED', 'FINAL_SUCCESS'):
                return self.executor.abort_unsigned(key, now)
            if last.broadcast_at is None and last.state in ('AUTHORIZED', 'SIGNED_DURABLE'):
                return self.executor.abort_unbroadcast(key, now)
        if (now >= state.intent.valid_until and (not state.attempts
                or state.attempts[-1].state in ('PREPARED', 'FINAL_SUCCESS'))):
            # No signature exists for the next step. Expiry must release this
            # intent instead of leaving authorize() to fail on every restart.
            return self.executor.abort_unsigned(key, now)
        if not state.attempts or state.attempts[-1].state=='FINAL_SUCCESS':
            if state.prepare_probes >= state.intent.max_prepare_probes:
                return self.executor.abort_unsigned(key, now)
            return self.executor.prepare(key,now)
        stage=state.attempts[-1].state
        if stage=='PREPARED':return self.executor.authorize(key,now)
        if stage in ('AUTHORIZED', 'SIGNED_DURABLE'):
            attempt = state.attempts[-1]
            gates = self.executor.guards.snapshot(state.intent, now)
            if now >= state.intent.valid_until:
                return self.executor.abort_unbroadcast(key, now)
            if (gates.epoch, gates.authority_version) != (attempt.epoch, attempt.guard_version):
                try:
                    return self.executor.reauthorize_unbroadcast(key, now)
                except Blocked:
                    return self.executor.abort_unbroadcast(key, now)
            if stage == 'AUTHORIZED':
                recovered = self.executor.recover_signature(key, now)
                if recovered.attempts[-1].state == 'SIGNED_DURABLE':
                    return recovered
                return self.executor.sign(key, now)
        if stage=='SIGNED_DURABLE':
            state=self.executor.broadcast(key,now)
            if state.attempts[-1].broadcast_at is not None and state.attempts[-1].state != 'REJECTED':
                self.observe(broadcast_observation(state,state.attempts[-1],wallet_id=self.wallet_id))
            return state
        return self.executor.reconcile(key,now)
