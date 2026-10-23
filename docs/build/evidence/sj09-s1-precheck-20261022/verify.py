"""SJ-09-PC01: offline check of whether the installed build can run the planned S1 rehearsal swap (IDEA-049-C SJ-09).

  python3.12 -I docs/build/evidence/sj09-s1-precheck-20261022/verify.py   (from a checkout of canonical)

No ports, keys, AWS or live calls. Inputs are the RC4 rehearsal inputs already in the repository and the
synthetic test fixtures. The S1 block is the test fixture (equal weights 1/5), not Keith's frozen weights.
Prints one JSON result; exits 1 if any check differs from the recorded expectation.
"""
from fractions import Fraction
from pathlib import Path
import hashlib, json, subprocess, sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from larp.contracts import ContractError, Document
from larp.runtime import gate_a
from larp.strategy.profiles import build_live_profiles, validate_live
from larp.strategy.schema import ceil, equity
from tests.strategy.test_s1_core import block

INSTALLED = 'd03bbb16cf51277c73d7f381b08f9551d0c10415'  # RC4 (LV-01), installed 2026-10-22 (IDEA-049-C SJ-06)
EV = ROOT / 'docs/build/evidence'
EW_PROFILE = EV / 'rehearsal-exit-split-20261021/rehearsal-deterministic.json'
results, failed = {}, []


def record(check, value, expected):
    results[check] = dict(value=value, expected=expected, status='AS_EXPECTED' if value == expected else 'DIFFERS')
    if value != expected:
        failed.append(check)


def refusal(call):
    """The innermost ContractError text: validate_live re-wraps every specific reason (see C2)."""
    try:
        call()
    except ContractError as error:
        inner = error
        while isinstance(inner.__cause__, ContractError):
            inner = inner.__cause__
        return dict(outer=str(error), inner=str(inner))
    return None


# C0: which runtime files these checks exercise differ from the installed build. Later canonical changes elsewhere in
# larp/ (for example IDEA-085's database pooling) do not affect them. Since 2026-10-23 exactly two changes do:
# PF-05 (PR256, planner.py: a stale mark never starts a cap trim) and SJ-11-RH01 (profiles.py and gate_a.py: the
# scoped S1 rehearsal, C2/C3). Before them this check was "no difference".
CHECKED = ['larp/contracts.py', 'larp/strategy', 'larp/risk', 'larp/runtime/gate_a.py', 'larp/runtime/gate_a_check.py',
           'larp/integration', 'config']
diff = subprocess.run(['git', '-C', str(ROOT), 'diff', '--name-only', INSTALLED, '--', *CHECKED],
                      capture_output=True, text=True, check=True)
record('C0_runtime_files_differing_from_installed_rc4', sorted(diff.stdout.split()),
       ['larp/risk/planner.py', 'larp/runtime/gate_a.py', 'larp/strategy/profiles.py'])

# The RC4 rehearsal gas and authority inputs (tools/deploy/build_rehearsal_candidate.py), with an S1 block.
doc = lambda path: Document.from_dict(json.loads(path.read_bytes()))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
authority = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
                 data_hash=sha(EV / 'ld02-execution-packet-20261020.json'))
budget = dict(action_units=384000000000000, sizing_units=80004608000000,
              decision_id='IDEA-049-C LD10-Q01 (Keegan delegation, 2026-10-21)',
              data_hash=sha(EV / 'signer-numeric-ceilings-20261021.json'))
summary, registry = EV / 'quotes-complete-20261020/quote-cost-summary.json', ROOT / 'config/intelligence/red_flags.v1.json'


def s1_profiles(s1):
    return build_live_profiles(doc(summary), doc(registry), s1=s1, s1_decision='SJ-09-PC01 probe (fixture block)',
                               initial_gas_only=True, authority=authority, gas_budget=budget)


s1 = s1_profiles(block())['REHEARSAL'].read()
validate_live(s1)
record('C1_s1_rehearsal_builds_and_validates', dict(
    evidence_mode=s1['evidence_mode'], falsifier_authority=s1['falsifier_authority'],
    minimum_trade_units=s1['minimum_trade_units'], per_trade_cap_units=s1['per_trade_cap_units'],
    exit_gas_reserve_units=s1['exit_gas_reserve_units'], gas_action_budget_units=s1['gas_action_budget_units']),
    dict(evidence_mode='BOUNDED_FALSIFIER', falsifier_authority='DISCRETIONARY_EXIT', minimum_trade_units=18637420,
         per_trade_cap_units=19100000, exit_gas_reserve_units=5 * 384000000000000,
         gas_action_budget_units=384000000000000))

# C2: S1 with SHADOW evidence and falsifiers (LD11-RH01's scope). Recorded 2026-10-22 as refused ("Live profile differs
# from decided v1 scope", re-wrapped as "Malformed or incomplete live profile"). SJ-11-RH01 admits it in REHEARSAL
# only, and validate_live now raises the specific reason itself, so the FINAL control shows it unwrapped.
shadow = dict(s1, evidence_mode='SHADOW', falsifier_authority='SHADOW')
scope = 'Live profile differs from decided v1 scope'
record('C2_s1_shadow_validate_live', dict(rehearsal=refusal(lambda: validate_live(shadow)),
                                          final=refusal(lambda: validate_live(dict(shadow, environment='FINAL')))),
       dict(rehearsal=None, final=dict(outer=scope, inner=scope)))

# C3: signed preparation without reviewed routing. Recorded 2026-10-22: only the EQUAL_WEIGHT scoped rehearsal
# passed. SJ-11-RH01: the S1 SHADOW rehearsal passes this check too (the probe's empty capture then stops it later);
# S1 with BOUNDED_FALSIFIER evidence is still refused.
def signed_prepare(profile):
    return lambda: gate_a.prepare({}, profile_raw=json.dumps(profile).encode(), capture_raw=b'{}', calendar_raw=b'{}',
                                  run_id='sj09-probe', build_id='0' * 40, now='2026-10-24T00:00:00Z',
                                  execution='service', runtime_mode='dev', adoption_ref='SJ-09-PC01 probe')
ew = json.loads(EW_PROFILE.read_bytes())
signed = 'Signed preparation needs reviewed routing or scoped deterministic rehearsal and an adoption reference'
record('C3_signed_prepare_without_routing', dict(
    s1_shadow_passes_this_check=(refusal(signed_prepare(shadow)) or {}).get('inner') != signed,
    s1_bounded=(refusal(signed_prepare(s1)) or {}).get('inner'),
    equal_weight_control_passes_this_check=(refusal(signed_prepare(ew)) or {}).get('inner') != signed),
    dict(s1_shadow_passes_this_check=True, s1_bounded=signed, equal_weight_control_passes_this_check=True))

# C4: a new run cannot start from a wallet that holds stocks (gate_a.initial_state; gate_a_check recomputes it).
from tests.runtime.test_gate_a import TOKENS, captured, profile as ga_profile, rehash
capture = captured()
capture['balances']['response']['data'][0]['tokenAssets'].append(dict(tokenContractAddress=TOKENS['NVDAB'],
                                                                      rawBalance=str(10**17)))
rehash(capture)
record('C4_initial_state_with_stock_holdings',
       (refusal(lambda: gate_a.initial_state(capture, ga_profile(), 'sj09-probe')) or {}).get('inner'),
       'Existing stock holdings require reviewed cost-basis history')

# C5: frozen weights at rehearsal capital. Every weight must keep a full high-level position above the minimum.
weights = {'GOOGLB': [22, 100], 'MSFTB': [26, 100], 'NVDAB': [17, 100], 'SKHYB': [15, 100], 'TSLAB': [20, 100]}
record('C5_unequal_weights_build', (refusal(lambda: s1_profiles(block(weights=weights))) or {}).get('inner'),
       'Measured minimum cannot fit a full position at REHEARSAL')
high = Fraction(19, 20)
w_min = Fraction(s1['minimum_trade_units'], 1) / (high * s1['expected_equity_units'])
record('C5_smallest_feasible_weight_at_100_usdt', str(round(float(w_min), 4)), '0.1962')

# C6: policy and planner at the rehearsal's cost ratio. The S1 planner fixture (tests/strategy/test_s1_plan.py) gets
# minimum_trade_units scaled so minimum / equity equals the rehearsal minimum over the dev wallet's start equity.
from larp.strategy.policy import decide
from tests.strategy.test_s1_plan import AT_95, FALLING, NAMES, first_intent, settled, snap
start_equity = 96_000_000 + 5325625054330011 * s1['quote_cost_summary']['bnb_price_units'] // 10**18
ratio = Fraction(s1['minimum_trade_units'], start_equity)


def at_ratio(scale, held=None, **kw):
    c = snap(held, **kw).context.read()
    e = equity(c['portfolio'], {m['symbol']: m for m in c['markets']}, allow_missing=True)
    s = snap(held, profile_changes=dict(minimum_trade_units=max(1, ceil(scale * e))), **kw)
    targets = sorted({(t.kind.name, t.reason) for t in decide(s, s.policy_state).targets})
    _, intent = first_intent(s)
    return dict(targets=[list(t) for t in targets], first_intent=intent['side'] if intent else None)


down = dict(held={n: AT_95 for n in NAMES}, state=settled([19, 20]), path=FALLING)
record('C6_policy_at_rehearsal_cost_ratio', dict(
    start_equity_units=start_equity, minimum_over_equity=str(round(float(ratio), 4)),
    flat_book=at_ratio(ratio)['first_intent'], up_to_down=at_ratio(ratio, **down),
    up_to_down_control_minimum_1=at_ratio(0, **down)),
    dict(start_equity_units=start_equity, minimum_over_equity='0.1867', flat_book='BUY',
         up_to_down=dict(targets=[['KEEP_QUANTITY', 'LOW_TURNOVER_HOLD']], first_intent=None),
         up_to_down_control_minimum_1=dict(targets=[['TARGET_WEIGHT', 'S1_LEVEL_CHANGE']], first_intent='SELL')))
# Equity below which a 19% S1 buy is under the minimum (the planner sizes on equity minus the cost reserve).
floor_units = ceil(Fraction(s1['minimum_trade_units']) / (high / 5)) + s1['cost_reserve_units']
record('C6_equity_floor_for_s1_buys_units', floor_units, 98191685)

# C7: exit reserve. The S1 builder still uses one child per position (LD10-P03-R1); two children need 10 actions.
# SJ-11-RH01 adds the two-child reserve to the S1 rehearsal candidate (tools/deploy/build_rehearsal_candidate.py),
# not to build_live_profiles, so these values are unchanged.
bnb = 5325625054330011
record('C7_exit_reserve_wei', dict(builder=s1['exit_gas_reserve_units'], two_child=10 * s1['gas_action_budget_units'],
                                   wallet_bnb_at_install=bnb, left_after_two_child=bnb - 10 * s1['gas_action_budget_units']),
       dict(builder=1920000000000000, two_child=3840000000000000, wallet_bnb_at_install=bnb,
            left_after_two_child=1485625054330011))

print(json.dumps(dict(schema='SJ09PreCheck.v1', record_id='SJ-09-PC01', installed_build=INSTALLED,
                      head=subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                          text=True).stdout.strip(),
                      checks=results, differs=failed), indent=1, sort_keys=True))
sys.exit(1 if failed else 0)
