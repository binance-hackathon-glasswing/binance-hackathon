"""DC-01: offline verification of the private completed export and public derived outputs.

From repo root: PYTHONPATH=. python <this file> --captures /path/to/export
Prints only derived statistics/hashes. Does not write, use credentials or call ports.
"""
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from larp.contracts import Document
from larp.execution import USDT
from larp.marketdata.cost_summary import FALLBACK_GAS_LIMIT, read_captures, summarize
from larp.marketdata.port import NATIVE, TOKENS
from larp.marketdata.web3 import READS, single
from larp.strategy.profiles import build_live_profiles

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition, label):
    if not condition:
        raise ValueError('Verification failed: ' + label)


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def gap(rows):
    times = sorted({r['at'] for r in rows})
    elapsed, start, end = max((int((stamp(b) - stamp(a)).total_seconds() * 1000), a, b)
                             for a, b in zip(times, times[1:]))
    return dict(milliseconds=elapsed, start=start, end=end)


def verify(captures):
    captures = Path(captures).resolve()
    manifest = (captures / 'SHA256SUMS').read_bytes()
    inventory, artifacts = {}, {}
    outcomes, endpoints, methods, raw_missing = Counter(), Counter(), Counter(), Counter()
    timings = defaultdict(list)
    for line in manifest.decode().splitlines():
        expected, name = line.split(maxsplit=1)
        path = (captures / name).resolve()
        check(path.is_relative_to(captures) and name not in inventory, 'manifest path/duplicate')
        raw = path.read_bytes()
        check(sha(raw) == expected, 'payload checksum')
        inventory[name] = dict(sha256=expected, bytes=len(raw))
        if name.startswith('artifacts/'):
            check(path.stem == expected, 'artifact content address')
            a = json.loads(raw)
            check(a['schema'] == 'Web3Observation.v1' and a['source_id'] == 'BINANCE_WEB3', 'artifact schema')
            check((a['method'], a['endpoint']) in READS, 'read/build endpoint')
            check(a['params']['binanceChainId'] == '56', 'chain binding')
            if 'response_body_base64' in a:
                body = base64.b64decode(a['response_body_base64'], validate=True)
                check(sha(body) == a['response_sha256'], 'response bytes hash')
                check(json.loads(body) == a['response'], 'parsed response equality')
            else:
                # The transport hashes non-JSON replies but retains no reversible
                # body. Keep that gap visible; never call it byte verification.
                raw_missing[a['outcome']] += 1
            artifacts[expected] = a
            outcomes[a['outcome']] += 1
            endpoints[a['endpoint']] += 1
            methods[a['method']] += 1
            timings[a['endpoint']].append(a['elapsed_ms'])
    check(set(p.name for p in captures.glob('capture-*.jsonl')) <= inventory.keys(), 'all daily files manifested')
    check(set(p.name for p in (captures / 'artifacts').iterdir()) ==
          {Path(n).name for n in inventory if n.startswith('artifacts/')}, 'all artifacts manifested')
    records = read_captures(captures)
    check(all(r['kind'] in ('SAMPLE', 'BNB_PRICE', 'FAILURE') for r in records), 'record kinds')
    samples = [r for r in records if r['kind'] == 'SAMPLE']
    prices = [r for r in records if r['kind'] == 'BNB_PRICE']
    references = Counter()

    def artifact(h, endpoint):
        a = artifacts[h]
        references[h] += 1
        check(a['endpoint'] == endpoint and a['outcome'] == 'ok' and a['http_status'] == 200, 'successful reference')
        check('response_body_base64' in a, 'referenced response bytes retained')
        return a

    def quote(h, pay, receive, amount):
        a = artifact(h, 'aggregator/quote-and-swap')
        p, rr = a['params'], single(a)['routerResult']
        check(p['vendor'] == rr['vendorName'] == 'LiquidMesh', 'vendor')
        check(p['fromTokenAddress'].lower() == rr['fromToken']['tokenContractAddress'].lower() == pay.lower(), 'pay token')
        check(p['toTokenAddress'].lower() == rr['toToken']['tokenContractAddress'].lower() == receive.lower(), 'receive token')
        check(int(p['amount']) == int(rr['fromTokenAmount']) == amount, 'input amount')
        check(int(rr['fromToken']['decimal']) == int(rr['toToken']['decimal']) == 18, 'token decimals')
        return a, rr

    wallets, sizes, token_detail = set(), set(), {}
    for r in samples:
        check(len(r['artifacts']) == 6 and r['gas_methods'] == ['FALLBACK', 'FALLBACK'], 'six references/all fallback')
        token = TOKENS[r['symbol']]
        buy, rb = quote(r['artifacts'][0], USDT, token, r['pay_raw'])
        sell, rs = quote(r['artifacts'][1], token, USDT, r['buy_received'])
        again, ra = quote(r['artifacts'][2], USDT, token, r['pay_raw'])
        for a in (buy, sell, again):
            wallets.add(a['params']['userWalletAddress'].lower())
        check(r['at'] == buy['available_at'] and r['token_decimals'] == 18, 'sample time/decimals')
        for field, rr in (('buy_received', rb), ('sell_proceeds', rs), ('requote_received', ra)):
            check(r[field] == int(rr['toTokenAmount']), 'output amount')
        check(Decimal(r['buy_impact_bps']) == Decimal(rb['priceImpactPercent']) * 100 and
              Decimal(r['sell_impact_bps']) == Decimal(rs['priceImpactPercent']) * 100, 'impact')
        check(r['trade_fee'] == rb.get('tradeFee'), 'legacy network-fee metadata')
        approvals = []
        for h, pay, amount in zip(r['artifacts'][3:5], (USDT, token), (r['pay_raw'], r['buy_received'])):
            a = artifact(h, 'aggregator/approve-transaction')
            check(a['params']['tokenContractAddress'].lower() == pay.lower() and
                  int(a['params']['approveAmount']) == amount and a['params']['vendor'] == 'LiquidMesh', 'approve binding')
            row = single(a)
            approvals.append(int(row['gasLimit']) * int(row['gasPrice']))
        check(r['approve_gas_wei'] == max(approvals), 'approve gas product')
        check(r['swap_gas_wei'] == [max(int(a['tx']['gas']), FALLBACK_GAS_LIMIT) * int(a['tx']['gasPrice'])
                                   for a in (single(buy), single(sell))], 'fallback gas product')
        meta = artifact(r['artifacts'][5], 'market/rwa/tokens')
        matches = [x for x in meta['response']['data'] if x['tokenContractAddress'].lower() == token.lower()]
        check(len(matches) == 1 and matches[0]['statusInfo']['openState'] == r['token_open'], 'open-state binding')
        sizes.add(r['pay_raw'])
    for r in prices:
        a, rr = quote(r['artifact'], USDT, NATIVE, r['pay_cash_units'] * 10**12)
        check(a['available_at'] == r['at'] and int(rr['toTokenAmount']) == r['received_wei'], 'BNB amount/time')
        wallets.add(a['params']['userWalletAddress'].lower())
    check(len(wallets) == 1, 'one public quote wallet')
    summary, report = summarize(records)
    check(summary == json.loads((HERE / 'quote-cost-summary.json').read_bytes()), 'summary reproduction')
    check(report == json.loads((HERE / 'quote-cost-summary.report.json').read_bytes()), 'report reproduction')
    profiles = build_live_profiles(Document.from_dict(summary),
                                  Document.from_dict(json.loads((ROOT / 'config/intelligence/red_flags.v1.json').read_bytes())))
    caps_raw = (ROOT / 'docs/build/evidence/signer-caps-proposal-20261017.json').read_bytes()
    caps = json.loads(caps_raw)['candidates']
    profile_detail = {}
    for env, doc in profiles.items():
        name = env.lower() + '-live.json'
        raw = (HERE / name).read_bytes()
        check(raw == doc.payload + b'\n', 'candidate profile reproduction')
        p = doc.read()
        policy = caps['development' if env == 'REHEARSAL' else 'final']['signing_policy']
        input_cap = int(policy['max_input_units'][USDT.lower()])
        profile_detail[name] = dict(file_sha256=sha(raw), document_sha256=doc.digest('StrategyProfile.v1'),
                                   baseline=p['baseline'], minimum_trade_units=p['minimum_trade_units'],
                                   per_trade_cap_units=p['per_trade_cap_units'], gas_top_up_cash_units=p['gas_top_up_cash_units'],
                                   fits_draft_35_usdt_dev_input_cap=(p['per_trade_cap_units'] <= 35_000_000 and
                                                                    p['gas_top_up_cash_units'] <= 35_000_000),
                                   applicable_draft_usdt_cap_raw=input_cap,
                                   fits_applicable_draft_cash_cap=max(p['per_trade_cap_units'], p['gas_top_up_cash_units']) * 10**12 <= input_cap)
    cap_screen = {}
    for env, candidate in caps.items():
        policy = candidate['signing_policy']
        cap_screen[env] = dict(
            cap_basis=policy['cap_basis'],
            buy_quotes_exceeding_usdt_cap=sum(r['pay_raw'] > int(policy['max_input_units'][USDT.lower()]) for r in samples),
            sell_quotes_exceeding_token_cap={s: sum(r['buy_received'] > int(policy['max_input_units'][token.lower()])
                                                   for r in samples if r['symbol'] == s) for s, token in TOKENS.items()},
            fallback_swaps_exceeding_fee_cap=sum(g > int(policy['max_fee_wei']) for r in samples for g in r['swap_gas_wei']),
            sample_max_approvals_exceeding_fee_cap=sum(r['approve_gas_wei'] > int(policy['max_fee_wei']) for r in samples))
    fee_exceptions = []
    fee_cap = int(caps['development']['signing_policy']['max_fee_wei'])
    for r in samples:
        for leg, g, h in zip(('BUY', 'SELL'), r['swap_gas_wei'], r['artifacts'][:2]):
            if g > fee_cap:
                tx = single(artifacts[h])['tx']
                fee_exceptions.append(dict(at=r['at'], symbol=r['symbol'], leg=leg, quote_artifact_sha256=h,
                                           fallback_fee_wei=g, quote_gas_limit=int(tx['gas']),
                                           fallback_gas_limit=max(int(tx['gas']), FALLBACK_GAS_LIMIT),
                                           gas_price_wei=int(tx['gasPrice']), draft_fee_cap_wei=fee_cap))
    for symbol in TOKENS:
        mine = [r for r in samples if r['symbol'] == symbol]
        token_detail[symbol] = dict(samples=len(mine), max_success_gap=gap(mine),
                                   sell_token_units_range=[min(r['buy_received'] for r in mine), max(r['buy_received'] for r in mine)])
    metadata = json.loads((captures / 'EXPORT-METADATA.json').read_bytes())
    check(metadata['samples_by_token'] == {s: t['samples'] for s, t in token_detail.items()}, 'export sample counts')
    check(metadata['bnb_quotes'] == len(prices) and metadata['artifact_files'] == len(artifacts), 'export counts')
    return dict(schema='CompletedQuoteCaptureVerification.v1', record_id='DC-01', result='PASS',
                capture_source_commit=metadata['capture_source_commit'], source_identity='EXPORT_METADATA_NOT_HOST_ATTESTATION',
                manifest_sha256=sha(manifest), verified_payload_files=len(inventory),
                daily_files={n: d for n, d in inventory.items() if n.startswith('capture-')},
                raw_artifacts=len(artifacts), raw_response_hashes_verified=len(artifacts) - sum(raw_missing.values()),
                response_bytes_unavailable=dict(raw_missing),
                referenced_artifacts=len(references), reference_occurrences=sum(references.values()),
                unreferenced_artifacts=len(artifacts.keys() - references.keys()),
                endpoints=dict(endpoints), artifact_outcomes=dict(outcomes), methods=dict(methods),
                api_elapsed_ms={e: dict(samples=len(v), p90=sorted(v)[(9*len(v)+9)//10-1], maximum=max(v))
                                for e, v in sorted(timings.items())},
                coverage=report['coverage'], first_record=min(r['at'] for r in records),
                latest_record=max(r['at'] for r in records), failures=[r for r in records if r['kind'] == 'FAILURE'],
                tokens=token_detail, bnb_max_success_gap=gap(prices), buy_cash_raw=sorted(sizes),
                swap_gas_methods=dict(Counter(m for r in samples for m in r['gas_methods'])),
                maximum_sample_approve_wei=max(r['approve_gas_wei'] for r in samples),
                maximum_fallback_swap_wei=max(g for r in samples for g in r['swap_gas_wei']),
                historical_caps_screen=dict(proposal_file_sha256=sha(caps_raw), candidates=cap_screen,
                                            fee_cap_exceptions=fee_exceptions,
                                            current_holdings_full_exits='NOT_SUPPLIED', approved=False),
                capture_hash=summary['capture_hash'], profile_candidates=profile_detail,
                fee_netting='UNVERIFIED', live_profile_acceptance=False, signed_caps_accepted=False,
                raw_data_committed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.captures), indent=2, sort_keys=True))
