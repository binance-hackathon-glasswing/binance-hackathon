"""IDEA-098 RC1-RC5: FS1 with allowance recovery, so the final can always sell after an aborted swap.

RC1 replays run 4's terminal flatten (2026-10-25): the first SELL's approve succeeds, its swap requote is refused
("encoded swap economics mismatch/expired"), and the open allowance then blocks every other name's SELL. Real
coordinator, planner, PostgreSQL execution registry and settlement (IDEA-096's AL2 harness); synthetic chain and venue.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from larp.contracts import Document
from larp.execution import Blocked, Executor, REVOKE_TOKENS, USDT, possible_swap_hashes
from larp.execution_live.service import map_command
from larp.execution_live.store import ExecutionStore
from larp.integration.runtime import ContextBuilder, initial_projection, ledger_from
from larp.integration.settlement import settle
from larp.marketdata.port import TOKENS
from larp.research.fixtures import with_quotes
from larp.storage.postgres import doc
from larp.strategy.profiles import validate_live
from tests import execution_fixtures as f
from tests.execution.test_allowance_recovery import Harness, Venue
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution import test_untrusted_router as u
from tests.integration.test_settlement import observation, command
from tests.runtime import test_s3_scheduled_flatten as persistence
from tests.strategy.test_s3_scheduled_flatten import AFTER_CLOSE, S3
from tests.strategy.test_execution_bounds import at, milliseconds
from tests.strategy.test_s1_plan import AT_95, NAMES
from tests.support import DatabaseCase

RUN = persistence.RUN
ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / 'docs/build/evidence/fs1-final-20261025'
REHEARSAL = ROOT / 'docs/build/evidence/fs1-rehearsal-20261025'
ACTION = 8 * 1_200_000 * 160_000_000  # IDEA-096 eight children at the CAP-02 signed ceilings
GAS = ('gas_action_budget_units', 'exit_gas_reserve_units')
REFUSED = 'encoded swap economics mismatch/expired'


class Run4Flatten(DatabaseCase):
    coordinator = persistence.ScheduledFlattenPersistence.coordinator
    start = persistence.ScheduledFlattenPersistence.start

    def flatten(self, *, recovery, persistent=False):
        """Run 4's terminal flatten with the first SELL's swap refused after its approve. `persistent`: every later
        SELL of that name is refused after its approve too (its market stays adverse). Returns the outcome."""
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        fixture = with_quotes(at(AFTER_CLOSE, profile_changes=S3, held={s: AT_95 for s in NAMES}))
        context = fixture.context.read()
        context['portfolio'].update(wallet_id=f.WALLET, bnb_units=10**9, bnb_decimals=18)
        template = next(q for m in context['markets'] for q in m['quotes'] if q['side'] == 'SELL')
        for row in context['markets']:
            row['quotes'] = [dict(template, quote_id='synthetic-exit-' + row['symbol'], pay_asset=row['symbol'],
                                  gas_bnb_units=10**7)]
        self.profile, self.profile_hash = context['profile'], fixture.policy_profile_hash
        self.now = milliseconds(AFTER_CLOSE)
        self.store.initialize(RUN, f.WALLET, 56, doc(initial_projection(context['portfolio'])))
        self.store.takeover(RUN, 1, offline=True)

        def market(now):
            rows = deepcopy(context['markets'])
            stamp = datetime.fromtimestamp(now / 1000, timezone.utc).isoformat()
            for row in rows:
                row.update(observed_at=stamp, available_at=stamp, close_at=stamp)
                for quote in row.get('quotes', []):
                    quote.update(observed_at=stamp, available_at=stamp, expires_at=datetime.fromtimestamp(
                        now / 1000 + 600, timezone.utc).isoformat())
            return rows
        calendar = lambda now: dict(index=80, remaining=10)
        calendar.window = lambda now: context['execution_session']
        self.builder = ContextBuilder(profile=self.profile, profile_hash=self.profile_hash, run_id=RUN,
            issuers={}, market=market, health=lambda current: context['health'], calendar=calendar)
        registry = ExecutionStore(self.store, run_id=RUN, wallet=f.WALLET)
        registry.install_test_schema()
        h = Harness.__new__(Harness)
        h.store, h.now = registry, self.now // 1000
        h.decoder = u.u.UntrustedRouterDecoder(u.policy())
        h.rpc = u.FakeRpc(h.decoder, f.WALLET, USDT, 0)
        h.decoder.bind(h.rpc)
        refused = {}  # intent_id -> requotes refused after its approve

        class Guards(ExecutionGuards):
            mode = 'live'

        class Signer(RegistrySigner):
            mode = 'live'

        class Run4Venue(Venue):
            def quote(self, i, nonce):
                # Run 4, 09:00Z: the first SELL's approve is final, then every requote of that intent is refused.
                target = i.intent_id == first.get('intent_id') or (persistent and i.pay_token == first.get('token'))
                if target and h.rpc.allowances.get(i.pay_token):
                    refused[i.intent_id] = refused.get(i.intent_id, 0) + 1
                    raise Blocked(REFUSED)
                p = super().quote(i, nonce)
                data = p.data
                for index, value, inner in ((u.u.AMOUNT, i.amount, False), (u.u.MINIMUM, i.minimum_output, False),
                        (u.u.QUOTED, i.minimum_output, False), (u.u.INNER_AMOUNT, i.amount, True),
                        (u.u.INNER_MINIMUM, i.minimum_output, True)):
                    data = u.u._set_word(data, index, value, inner=inner)
                return replace(p, data=data)
        h.guards, h.venue = Guards(registry), Run4Venue(registry)
        h.executor = Executor(registry, h.guards, h.venue, Signer(registry), h.decoder, allowance_recovery=recovery)
        first, outcome = {}, dict(sold=[], aborted=[], blocked=[], ordinals={}, allowance_blocks=0)
        for n in range(30):
            self.now = h.now * 1000
            c = self.coordinator()
            name = 'flatten-' + str(n)
            plan = self.start(c, name)
            if not plan['intents']:
                break
            for planned in plan['intents']:
                self.assertEqual(planned['side'], 'SELL')
                leg = planned['execution_bounds']['leg']
                outcome['ordinals'][leg] = max(outcome['ordinals'].get(leg, 0), planned['execution_bounds']['ordinal'])
                first.setdefault('intent_id', planned['intent_id'])
                first.setdefault('token', TOKENS[planned['symbol']])
                i = map_command(command(planned, name), run_id=RUN, wallet=f.WALLET,
                    version_id='s3-review-fixture', router=h.decoder.router,
                    token_decimals={s: 4 for s in NAMES}, limits=dict(per_trade_cap_units=50_000_000,
                        max_gas=300000, max_gas_price=10, gas_budget=10**7), now_ms=self.now)
                h.executor.create(i, h.now)
                state = self.drive(h, c, i, planned, name, last=planned == plan['intents'][-1], outcome=outcome)
                if i.intent_id == first['intent_id']:
                    outcome['after_first_abort'] = dict(h.rpc.allowances)
                (outcome['sold'] if state.status == 'COMPLETED' else outcome['aborted']).append(planned['symbol'])
            c.close(name, h.now * 1000, 'COMPLETE')
            h.now += 1
        current = self.store.load(RUN).read()
        outcome.update(ledger=ledger_from(current['projection'], current['reservations']),
                       reservations=current['reservations'], allowances=dict(h.rpc.allowances), refused=refused,
                       first=first['intent_id'])
        return outcome

    def drive(self, h, c, i, planned, name, *, last, outcome):
        """The execution service's loop for one intent (`larp/execution_live/service.py`), with observations."""
        e = h.executor
        while True:
            state = e._load(i.key)
            if state.status != 'ACTIVE':
                break
            h.now += 1
            final = state.attempts[-1] if state.attempts else None
            ready = (final is None or final.state == 'FINAL_SUCCESS'
                     or (state.abort_pending and final.state in {'ABORTED', 'NOT_SUBMITTED'}))
            if h.now >= i.valid_until and (final is None or final.state in ('PREPARED', 'FINAL_SUCCESS')):
                e.abort_unsigned(i.key, h.now)
                continue
            if ready and state.prepare_probes >= i.max_prepare_probes:
                e.abort_unsigned(i.key, h.now)
                continue
            state = e.prepare(i.key, h.now)
            if state.blocked_reason and 'allowance' in state.blocked_reason:
                outcome['allowance_blocks'] += 1
            if state.status != 'ACTIVE' or not state.attempts or state.attempts[-1].state != 'PREPARED':
                continue
            for method in (e.authorize, e.sign, e.broadcast):
                h.now += 1
                state = method(i.key, h.now)
            a = state.attempts[-1]
            h.venue.outcomes[a.tx_hash] = f.finalized(a, 'SUCCESS')
            h.now += 3
            a = e.reconcile(i.key, h.now).attempts[-1]  # with its receipt gas
            h.guards.nonce += 1
            if a.step in REVOKE_TOKENS:
                h.rpc.allowances[REVOKE_TOKENS[a.step]] = 0
            elif a.step == 'APPROVE':
                h.rpc.allowances[i.pay_token] = i.amount
            elif a.step == 'SWAP':
                h.rpc.allowances[i.pay_token] = 0
            stamp = datetime.fromtimestamp(h.now, timezone.utc).isoformat()
            common = dict(run_id=RUN, wallet_id=f.WALLET, observed_at=stamp, tx_hash=a.tx_hash,
                          attempt_id=a.attempt_id, step=a.step.lower())
            maintenance = (dict(maintenance='ALLOWANCE_REVOKE', token_contract=REVOKE_TOKENS[a.step],
                                spender=i.router, approved_amount='0') if a.step in REVOKE_TOKENS else {})
            c.observe(a.attempt_id + ':send', Document.from_dict(observation(planned, name, a.attempt_id + ':send',
                'BROADCAST_ATTEMPTED', **common, **maintenance)), settle)
            fill = dict(symbol=planned['symbol'], side='SELL', token_units=planned['token_units'],
                        cash_units=planned['min_receive_units'], fee_units=0) if a.step == 'SWAP' else {}
            c.observe(a.attempt_id + ':final', Document.from_dict(observation(planned, name, a.attempt_id + ':final',
                'FILL' if a.step == 'SWAP' else 'APPROVAL', **common, **maintenance, **fill, gas_bnb_units=a.gas_used,
                gas_value_units=1, intent_terminal=a.step == 'SWAP', round_terminal=a.step == 'SWAP' and last)),
                settle)
        if state.status == 'ABORTED':
            self.assertFalse(possible_swap_hashes(state))
            stamp = datetime.fromtimestamp(h.now, timezone.utc).isoformat()
            c.observe(i.key + ':not-submitted', Document.from_dict(observation(planned, name,
                i.key + ':not-submitted', 'NOT_SUBMITTED', run_id=RUN, wallet_id=f.WALLET, observed_at=stamp, reason='ABORTED_BEFORE_SWAP_BROADCAST',
                round_terminal=last)), settle)
        return state

    def test_rc1_with_recovery_an_aborted_sell_is_cleaned_up_and_every_name_reaches_dust(self):
        out = self.flatten(recovery=True)
        first = out['refused']
        self.assertEqual(1, len(first), out)  # the first SELL's requote was refused once, then cleaned up
        self.assertEqual(1, len(out['aborted']), out)
        self.assertEqual(set(NAMES), set(out['sold']))
        self.assertTrue(all(p['units'] <= self.profile['dust_units'] for p in out['ledger']['positions'].values()),
                        out['ledger']['positions'])
        self.assertFalse(out['reservations'])
        self.assertFalse(any(out['allowances'].values()), out['allowances'])
        self.assertEqual(0, out['allowance_blocks'])
        limit = self.profile['s1']['execution']['max_attempts_per_leg_session']
        self.assertLessEqual(max(out['ordinals'].values()), limit, out['ordinals'])
        print('RC1 recovery', {k: out[k] for k in ('sold', 'aborted', 'ordinals', 'refused')})

    def test_rc1_without_recovery_the_abort_leaves_the_allowance_open(self):
        """Pre-registered prediction NOT met here (IDEA-098 results): the planner re-plans the aborted name first, its
        own approve overwrites the allowance and its swap consumes it, so this flatten still ends flat. Run 4 stuck
        because RC7 planned another name next (NVDAB at 09:30Z). What holds: the abort leaves the allowance open."""
        out = self.flatten(recovery=False)
        token = TOKENS[out['aborted'][0]]
        self.assertTrue(out['after_first_abort'][token], out['after_first_abort'])
        print('RC1 no recovery', {k: out[k] for k in ('sold', 'aborted', 'ordinals', 'allowance_blocks')})

    def test_rc1x_one_name_stays_adverse_recovery_still_sells_the_other_four(self):
        """Exploratory (added after the RC1 run, not pre-registered): every SELL of the first name is refused after
        its approve. With recovery each abort is cleaned up, the other four reach dust, and the adverse name stops at
        its leg attempt limit with no allowance open. Without recovery its open allowance blocks the others."""
        limit = 5
        on = self.flatten(recovery=True, persistent=True)
        stuck = {s for s, p in on['ledger']['positions'].items() if p['units'] > self.profile['dust_units']}
        self.assertEqual(1, len(stuck), on['ledger']['positions'])
        self.assertEqual(set(NAMES) - stuck, set(on['sold']))
        self.assertFalse(any(on['allowances'].values()), on['allowances'])
        self.assertLessEqual(max(on['ordinals'].values()), limit, on['ordinals'])
        self.assertFalse(on['reservations'])
        off = self.flatten(recovery=False, persistent=True)
        held = {s for s, p in off['ledger']['positions'].items() if p['units'] > self.profile['dust_units']}
        print('RC1x recovery', {k: on[k] for k in ('sold', 'aborted', 'ordinals')}, stuck)
        print('RC1x no recovery', {k: off[k] for k in ('sold', 'aborted', 'ordinals', 'allowance_blocks')}, held)
        self.assertGreater(len(held), 1, off['ledger']['positions'])
        self.assertTrue(any(off['allowances'].values()))
        self.assertGreater(off['allowance_blocks'], 0)


# --- RC2/RC3: the recovery profiles and the idempotent opt-in -------------------------------------------------------

def _profiles(directory, name):
    off, on = (json.loads((directory / f).read_bytes()) for f in (name + '.json', name + '-recovery.json'))
    return off, on


def test_rc2_recovery_profiles_rebuild_and_differ_only_in_the_recovery_gas():
    from tools.deploy import build_final_candidate as final, build_rehearsal_candidate as rehearsal
    block = (FINAL / 'fs1-block.json').read_bytes()
    for directory, name, build in (
            (FINAL, 'fs1-final', lambda decision, **o: final.build(s1_raw=block, s1_decision=decision, **o)),
            (REHEARSAL, 'fs1-rehearsal', lambda decision, **o: rehearsal.build(
                2, s1_raw=block, s1_decision=decision, fs1_rehearsal=True, **o))):
        off, on = _profiles(directory, name)
        decision = off['provenance']['s1']['decision_id']
        assert build(decision).payload + b'\n' == (directory / (name + '.json')).read_bytes()
        assert build(decision, allowance_recovery=True).payload + b'\n' == \
            (directory / (name + '-recovery.json')).read_bytes()
        validate_live(on)
        assert {k for k in set(off) | set(on) if off.get(k) != on.get(k)} == {*GAS, 'provenance'}
        assert {k for k in on['provenance'] if on['provenance'][k] != off['provenance'][k]} == {
            *GAS, 'gas_sizing_budget_units'}
        assert (on['gas_action_budget_units'], on['exit_gas_reserve_units']) == (ACTION, 5 * 2 * ACTION)
        assert on['gas_sizing_budget_units'] == off['gas_sizing_budget_units']
        assert on['provenance']['gas_action_budget_units']['data_hash'] == hashlib.sha256(
            (ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes()).hexdigest()


def recovery_inputs(profile):
    from tests.execution import test_caps_review as caps
    c = caps.CapsReview('test_pins_and_private_output_no_overwrite_or_content_echo')
    c.setUp()
    c.config.update(untrusted_router_policy_file='/synthetic/policy.json', untrusted_router_policy_sha256='a' * 64,
                    max_gas=1_200_000, max_gas_price=160_000_000, mode='live')
    c.ledger['mode'], c.inputs['environment'] = 'live', profile['environment']
    from larp.execution import NATIVE_BNB
    c.policy['allowed_tokens'].remove(NATIVE_BNB)
    c.inputs['quote_artifacts'] = [ref for ref in c.inputs['quote_artifacts'] if ref['path'] != 'BNB.json']
    runtime = {k: c.config[k] for k in ('run_id', 'build_id', 'wallet_address', 'mode')}
    runtime['driver'] = {k: c.config[k] for k in ('untrusted_router_policy_file', 'untrusted_router_policy_sha256')}
    c.profile = profile
    return c, runtime


def test_rc3_the_opt_in_keeps_the_pinned_recovery_profile_and_agrees_with_it_from_the_cleanup_off_profile():
    from tools.deploy.enable_allowance_recovery import candidate
    off, on = _profiles(FINAL, 'fs1-final')
    c, runtime = recovery_inputs(on)
    try:
        files = candidate(on, c.config, c.policy, runtime, decision_id='IDEA-098 RC3')
        assert files['profile.json'] == (FINAL / 'fs1-final-recovery.json').read_bytes()
        sha = hashlib.sha256(files['profile.json']).hexdigest()
        execution, policy, run = (json.loads(files[n]) for n in
                                  ('execution-config.json', 'signing-policy.json', 'runtime.json'))
        assert (execution['allowance_recovery'], policy['allowance_recovery'], run['driver']['allowance_recovery']) \
            == (True, True, True)
        assert (execution['gas_budget'], execution['strategy_profile_sha256'], run['driver']['strategy_profile_sha256']) \
            == (ACTION, sha, sha)
        derived = json.loads(candidate(off, c.config, c.policy, runtime, decision_id='IDEA-098 RC3')['profile.json'])
        assert {k: derived[k] for k in (*GAS, 'gas_sizing_budget_units')} == \
            {k: on[k] for k in (*GAS, 'gas_sizing_budget_units')}
    finally:
        c.doCleanups()


def test_rc4_caps_review_gas_rows_cover_the_final_recovery_profile_at_the_cap_02_ceilings():
    """The recovery gas rows are COVERED. The synthetic caps fixture is rehearsal-sized, so two non-gas rows stay
    BLOCKED: its signer policy allows 35 USDT per input (FS1's per-trade cap is 38.2) and its quotes are priced at
    2 gwei (above the 0.16 gwei ceiling). The real M3 review with FS1-size quotes and the final policy decides those."""
    from tools.deploy.enable_allowance_recovery import candidate
    _, on = _profiles(FINAL, 'fs1-final')
    c, runtime = recovery_inputs(on)
    try:
        files = candidate(on, c.config, c.policy, runtime, decision_id='IDEA-098 RC4')
        c.profile, c.config, c.policy = (json.loads(files[n]) for n in
                                         ('profile.json', 'execution-config.json', 'signing-policy.json'))
        c.ledger['bnb_units'] = c.profile['exit_gas_reserve_units']
        c.save_inputs()
        result = c.report()
        rows = {row['check']: row for row in result['checks']}
        for name, required in (('INITIAL_SIGNED_CHILD_GAS_ENVELOPE', ACTION), ('INITIAL_PROFILE_ACTION_BUDGET', ACTION),
                               ('INITIAL_BNB_EXIT_RESERVE', 5 * 2 * ACTION)):
            assert (rows[name]['required'], rows[name]['covered']) == (str(required), True), rows[name]
        assert set(result['blockers']) == {'FULL_POSITION_USDT', 'QUOTE_EXCEEDS_EXECUTION_GAS_LIMITS',
                                           'OWNER_REVIEW_REQUIRED', 'POLICY_APPROVAL_REQUIRED'}, result['blockers']
        c.config['gas_budget'] -= 1
        c.save_inputs()
        assert 'INITIAL_SIGNED_CHILD_GAS_ENVELOPE' in c.report()['blockers']
        c.config['gas_budget'] += 1
        c.ledger['bnb_units'] -= 1
        c.save_inputs()
        assert 'INITIAL_BNB_EXIT_RESERVE' in c.report()['blockers']
    finally:
        c.doCleanups()


# --- RC5: Gate A preparation with the opt-in ---------------------------------------------------------------------

def test_rc5_signed_live_and_dev_preparation_carry_the_opt_in_and_pass_the_gate_check():
    from larp.runtime import gate_a_check
    from tests.strategy import test_fs1_final as fs1
    from tests.strategy import test_s1_rehearsal as rh
    from tests.strategy import test_s2_weekend as s2
    _, final = _profiles(FINAL, 'fs1-final')
    files = fs1.live_prepared(final, **s2.POLICY, allowance_recovery=True)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    assert values['runtime.json']['driver']['allowance_recovery'] is True
    assert values['preparation-report.json']['allowance_recovery'] is True
    assert values['strategy-profile.json'] == final
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    _, rehearsal = _profiles(REHEARSAL, 'fs1-rehearsal')
    files = rh.prepared(rehearsal, **s2.POLICY, allowance_recovery=True)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    assert values['runtime.json']['driver']['allowance_recovery'] is True
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)


def test_rc6_install_sheet_and_readme_name_the_recovery_profile():
    sha = hashlib.sha256((FINAL / 'fs1-final-recovery.json').read_bytes()).hexdigest()
    sheet = (ROOT / 'docs/build/ops/final-fs1/README.md').read_text()
    readme = (FINAL / 'README.md').read_text()
    assert sha in sheet and sha in readme
    assert '--allowance-recovery' in sheet and 'enable_allowance_recovery' in sheet
    rehearsal_sha = hashlib.sha256((REHEARSAL / 'fs1-rehearsal-recovery.json').read_bytes()).hexdigest()
    assert rehearsal_sha in (REHEARSAL / 'README.md').read_text()
