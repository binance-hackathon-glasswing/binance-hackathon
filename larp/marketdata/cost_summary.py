"""IDEA-057: measure quote costs read-only, then summarise them as QuoteCostSummary.v1 (Gate A input 1).

`capture` (needs the Web3 key pair) records, per round and bStock: a buy quote, a sell quote for exactly the bought
units, a re-quote of the buy after the proposal lifetime, the approve transactions for both pay tokens and gas
estimates for both swaps; plus one USDT -> BNB quote for the BNB price. Each sample names the raw response artifacts
that `Web3Client` stored. It never signs, approves or broadcasts, and reads no wallet key or ai-seeds secret.

`summarize` (offline) turns every capture into the summary `larp.strategy.profiles.build_live_profiles` consumes,
plus a report of coverage, failures, fallbacks and parameters. The tokens trade 24/7, so costs are split into US-session
and off-session regimes and each field takes the worse. Quoted costs are not realised fills (ledger rule 4).

    python -m larp.marketdata.cost_summary capture --address 0x<public> --out-dir DIR [--rounds N] [--interval-seconds S]
    python -m larp.marketdata.cost_summary summarize --captures DIR --output summary.json
"""

import argparse
from datetime import datetime, timezone
from decimal import ROUND_CEILING, Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from larp.contracts import ContractError
from larp.execution import USDT
from .port import NATIVE, TOKENS, MarketPort, integer, number
from .web3 import Unavailable, data, encoded, single

FALLBACK_GAS_LIMIT = 1_116_000  # 1.2 x the kit's largest observed route (930k gas), participant-kit.md K8
QUOTE_TTL_SECONDS = 30  # "bStock quotes ... expire after about 30 s" (kit, F-96); the API returns no expiry
# The tokens trade 24/7 (SKILL.md Q-32): costs are measured inside and outside the US regular session (IDEA-054).
SESSION_CALENDAR = Path(__file__).resolve().parents[2] / 'config' / 'runtime' / 'session-calendar.2026.json'
REGIMES = ('US_SESSION', 'OFF_SESSION')
WORSE_OF_REGIMES = ('median_impact_bps', 'spread_bps', 'approve_gas_bnb_units', 'swap_gas_bnb_units', 'slippage_bps')
# Outcomes no later round can recover from: the capture stops instead of recording failures for days.
FATAL_OUTCOMES = frozenset({'authentication_error', 'compliance_restriction'})


def _fatal(error):
    return isinstance(error, ContractError) or (isinstance(error, Unavailable) and str(error) in FATAL_OUTCOMES)


def _first(record):
    result = data(record)
    if isinstance(result, list):
        if not result or type(result[0]) is not dict:
            raise Unavailable('unexpected response shape')
        return result[0]
    if type(result) is not dict:
        raise Unavailable('unexpected response shape')
    return result


def _swap_gas(market, tx, wallet, fallback):
    """The kit's swap gas rule, in wei: max(tx.gas, ceil(1.2 x estimate)) x gasPrice; the fallback when it fails."""
    price = integer(tx['gasPrice'])
    try:
        record = market.call('pre-transaction/gas-limit', dict(evmTx=dict(
            **{'from': wallet}, to=tx['to'], data=tx['data'], value=str(int(tx.get('value') or 0)))), method='POST')
        estimate = integer(_first(record)['gasLimit'])
        limit, method, artifact = max(integer(tx['gas']), math.ceil(estimate * 12 / 10)), 'ESTIMATED', \
            record['artifact_sha256']
    except (Unavailable, KeyError, TypeError, ValueError):
        limit, method, artifact = max(integer(tx['gas']), fallback), 'FALLBACK', None
    return limit * price, method, artifact


def _approve_gas(market, token, amount, vendor):
    record = market.call('aggregator/approve-transaction', dict(tokenContractAddress=token, approveAmount=str(amount),
                                                                vendor=vendor))
    row = _first(record)
    return integer(row['gasLimit']) * integer(row['gasPrice']), record['artifact_sha256']


def _quote(market, symbol, side, amount, pay, receive):
    record = market.quote(symbol, side, amount, 18)
    q = single(record)
    rr, tx = q['routerResult'], q['tx']
    if (str(rr['fromToken']['tokenContractAddress']).lower() != pay.lower()
            or str(rr['toToken']['tokenContractAddress']).lower() != receive.lower()
            or integer(rr['fromTokenAmount']) != amount or integer(rr['toTokenAmount']) <= 0):
        raise Unavailable('quote token/amount binding failed')
    return record, rr, tx


def capture_round(market: MarketPort, *, cash_units=40_000_000, requote_seconds=15,
                  fallback_gas_limit=FALLBACK_GAS_LIMIT, sleep=time.sleep):
    """One round over the five bStocks. Returns SAMPLE, FAILURE and BNB_PRICE records; never raises for one token."""
    if type(cash_units) is not int or cash_units <= 0 or requote_seconds < 0 or fallback_gas_limit <= 0:
        raise ContractError('Invalid capture parameters')
    pay = cash_units * 10**12  # chain USDT has 18 decimals; money units have 6
    records, open_state, meta_artifacts = [], {}, []
    try:  # openState per token (GAP-44): the tokens trade 24/7, but no order is placed while it is false (F-95)
        for symbol, (row, record) in market.metadata().items():
            status = row.get('statusInfo')
            state = status.get('openState') if isinstance(status, dict) else None
            open_state[symbol] = state if type(state) is bool else None
            meta_artifacts = [record['artifact_sha256']]
    except Unavailable as error:
        if _fatal(error):
            raise
        records.append(dict(kind='FAILURE', symbol=None, stage='TOKEN_STATUS', reason=str(error), at=_now()))
    for symbol, token in TOKENS.items():
        stage = 'BUY_QUOTE'
        try:
            buy, rr_buy, tx_buy = _quote(market, symbol, 'BUY', pay, USDT, token)
            received = integer(rr_buy['toTokenAmount'])
            stage = 'SELL_QUOTE'
            sell, rr_sell, tx_sell = _quote(market, symbol, 'SELL', received, token, USDT)
            stage = 'REQUOTE'
            sleep(requote_seconds)
            requote, rr_again, _ = _quote(market, symbol, 'BUY', pay, USDT, token)
            stage = 'APPROVE'
            vendor = rr_buy.get('vendorName') or 'LiquidMesh'
            approve_cash, a1 = _approve_gas(market, USDT, pay, vendor)
            approve_token, a2 = _approve_gas(market, token, received, rr_sell.get('vendorName') or vendor)
            stage = 'GAS_ESTIMATE'
            buy_gas, buy_method, e1 = _swap_gas(market, tx_buy, market.wallet, fallback_gas_limit)
            sell_gas, sell_method, e2 = _swap_gas(market, tx_sell, market.wallet, fallback_gas_limit)
            stage = 'RECORD'
            records.append(dict(
                kind='SAMPLE', symbol=symbol, at=buy['available_at'], pay_raw=pay,
                token_decimals=integer(rr_buy['toToken']['decimal']), buy_received=received,
                sell_proceeds=integer(rr_sell['toTokenAmount']), requote_received=integer(rr_again['toTokenAmount']),
                buy_impact_bps=str(number(rr_buy['priceImpactPercent']) * 100),
                sell_impact_bps=str(number(rr_sell['priceImpactPercent']) * 100),
                approve_gas_wei=max(approve_cash, approve_token), swap_gas_wei=[buy_gas, sell_gas],
                gas_methods=[buy_method, sell_method], trade_fee=rr_buy.get('tradeFee'),
                token_open=open_state.get(symbol),
                artifacts=[buy['artifact_sha256'], sell['artifact_sha256'], requote['artifact_sha256'], a1, a2,
                           *[e for e in (e1, e2) if e], *meta_artifacts]))
        except (Unavailable, KeyError, TypeError, ValueError) as error:
            if _fatal(error):
                raise
            records.append(dict(kind='FAILURE', symbol=symbol, stage=stage, reason=str(error) or type(error).__name__,
                                at=_now()))
    try:
        record = market.call('aggregator/quote-and-swap', dict(
            amount=str(pay), fromTokenAddress=USDT, toTokenAddress=NATIVE, userWalletAddress=market.wallet,
            vendor='LiquidMesh', slippagePercent='0.5'))
        rr = single(record)['routerResult']
        if (str(rr['toToken']['tokenContractAddress']).lower() != NATIVE or integer(rr['toToken']['decimal']) != 18
                or integer(rr['fromTokenAmount']) != pay):
            raise Unavailable('BNB quote binding failed')
        records.append(dict(kind='BNB_PRICE', at=record['available_at'], pay_cash_units=cash_units,
                            received_wei=integer(rr['toTokenAmount']), artifact=record['artifact_sha256']))
    except (Unavailable, KeyError, TypeError, ValueError) as error:
        if _fatal(error):
            raise
        records.append(dict(kind='FAILURE', symbol='BNB', stage='BNB_QUOTE', reason=str(error) or type(error).__name__,
                            at=_now()))
    return records


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


# ---------------------------------------------------------------------------------------------------------- summary
def _median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _p90(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.9 * len(ordered)) - 1]  # nearest rank


def _ceil(value):
    return int(Decimal(value).to_integral_value(rounding=ROUND_CEILING))


def _day(at):
    return datetime.fromisoformat(at.replace('Z', '+00:00')).astimezone(timezone.utc).date()


def _instant_ms(at):
    moment = datetime.fromisoformat(at.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('naive time')
    return int(moment.timestamp() * 1000)


def _regime(at, sessions):
    """US_SESSION while the underlying's regular session is open, else OFF_SESSION (nights, weekends, holidays)."""
    ms = _instant_ms(at)
    if ms < sessions[0][1] or ms >= sessions[-1][2]:
        raise ContractError('Sample outside the session calendar: ' + at)
    return 'US_SESSION' if any(opened <= ms < closed for _, opened, closed in sessions) else 'OFF_SESSION'


def _costs(mine, quote_ttl_seconds):
    """One regime's cost row for one token, plus its fallback-gas count."""
    impacts, residuals, drifts, approves, swaps, fallbacks = [], [], [], [], [], 0
    for r in mine:
        pay, buy_impact, sell_impact = integer(r['pay_raw']), Decimal(r['buy_impact_bps']), \
            Decimal(r['sell_impact_bps'])
        roundtrip = Decimal(pay - integer(r['sell_proceeds'])) * 10000 / pay
        impacts += [buy_impact, sell_impact]
        residuals.append(roundtrip - buy_impact - sell_impact)
        buy = integer(r['buy_received'])
        drifts.append(abs(Decimal(buy - integer(r['requote_received']))) * 10000 / buy)
        approves.append(integer(r['approve_gas_wei']))
        if len(r['swap_gas_wei']) != 2 or len(r['gas_methods']) != 2:
            raise ContractError('Each sample needs buy and sell swap gas')
        swaps += [integer(g) for g in r['swap_gas_wei']]
        fallbacks += sum(m == 'FALLBACK' for m in r['gas_methods'])
    return dict(samples=len(mine), median_impact_bps=max(1, _ceil(_median(impacts))),
                spread_bps=max(0, _ceil(_median(residuals))), fee_bps=0,
                approve_gas_bnb_units=_p90(approves), swap_gas_bnb_units=_p90(swaps),
                slippage_bps=min(50, max(1, _ceil(_p90(drifts)))), quote_ttl_seconds=quote_ttl_seconds), fallbacks


def summarize(records, *, min_samples=10, min_days=3, require_weekend=True, quote_ttl_seconds=QUOTE_TTL_SECONDS,
              calendar=SESSION_CALENDAR):
    """(QuoteCostSummary.v1, report). Raises ContractError naming every unmet coverage or consumer requirement.

    The tokens trade 24/7 (SKILL.md Q-32), so each token needs `min_samples` both inside and outside the US regular
    session (`calendar`, a frozen USRegularSessions.v1), and each cost field is the worse of the two regimes: the
    profile must hold whenever the agent trades, whatever share of the capture fell in either regime."""
    from larp.runtime.driver import SessionCalendar
    from larp.strategy.profiles import quote_summary
    raw = Path(calendar).read_bytes()
    try:
        sessions = SessionCalendar(json.loads(raw)).sessions
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError('Invalid session calendar: ' + str(error)) from None
    try:
        samples = [r for r in records if r['kind'] == 'SAMPLE']
        prices = [r for r in records if r['kind'] == 'BNB_PRICE']
        failures = [r for r in records if r['kind'] == 'FAILURE']
        rows, detail, symbol_days, regime_counts = {}, {}, {}, {}
        with localcontext() as context:
            context.prec = 60
            for symbol in TOKENS:
                mine = [r for r in samples if r['symbol'] == symbol]
                symbol_days[symbol] = sorted({_day(r['at']) for r in mine})
                by_regime = {regime: [r for r in mine if _regime(r['at'], sessions) == regime] for regime in REGIMES}
                regime_counts[symbol] = {regime: len(rs) for regime, rs in by_regime.items()}
                measured = {regime: _costs(rs, quote_ttl_seconds) for regime, rs in by_regime.items() if rs}
                if not measured:
                    continue
                rows[symbol] = dict(next(iter(measured.values()))[0], samples=len(mine))
                for field in WORSE_OF_REGIMES:
                    rows[symbol][field] = max(row[field] for row, _ in measured.values())
                detail[symbol] = dict(
                    samples=len(mine), utc_days=[d.isoformat() for d in symbol_days[symbol]],
                    fallback_gas_estimates=sum(f for _, f in measured.values()),
                    failures=sum(f.get('symbol') == symbol for f in failures),
                    trade_fees=sorted({str(r.get('trade_fee')) for r in mine}),
                    regimes={regime: dict(row, fallback_gas_estimates=f, token_open={
                        str(state).lower(): sum(r.get('token_open') is state for r in by_regime[regime])
                        for state in (True, False, None)}) for regime, (row, f) in measured.items()})
            price_units = [Decimal(integer(p['pay_cash_units'])) * 10**18 / integer(p['received_wei'])
                           for p in prices]
    except (KeyError, TypeError, ValueError, ZeroDivisionError, ArithmeticError, Unavailable) as error:
        if type(error) is ContractError:
            raise
        raise ContractError('Malformed capture record: ' + type(error).__name__) from None
    days = sorted(set().union(*symbol_days.values()))
    weekend = [d for d in days if d.weekday() >= 5]
    problems = []
    for s in TOKENS:  # coverage per token: one token's weekday-only samples must not ride on another's weekend
        mine = symbol_days[s]
        for regime, count in regime_counts[s].items():
            if count < min_samples:
                problems.append(f'{s}: {count} {regime} samples < {min_samples}')
        if len(mine) < min_days:
            problems.append(f'{s}: {len(mine)} UTC days < {min_days}')
        if require_weekend and not any(d.weekday() >= 5 for d in mine):
            problems.append(f'{s}: no weekend sample')
    if not price_units:
        problems.append('no BNB price quote')
    if problems:
        raise ContractError('Capture coverage incomplete: ' + '; '.join(problems))
    canonical = sorted(encoded(r).decode() for r in samples + prices)
    capture_hash = hashlib.sha256(encoded(canonical)).hexdigest()
    summary = dict(schema='QuoteCostSummary.v1', origin='RECORDED_WEB3', capture_hash=capture_hash,
                   observed_at=max(r['at'] for r in samples + prices),
                   bnb_price_units=int(_median(price_units)), bnb_decimals=18, symbols=rows)
    quote_summary(summary)  # the consumer's own check; a token whose costs leave no gas budget refuses here
    report = dict(schema='QuoteCostReport.v1', capture_hash=capture_hash, measurement='QUOTED_COSTS_NOT_FILLS',
                  coverage=dict(utc_days=[d.isoformat() for d in days], weekend_days=[d.isoformat() for d in weekend],
                                samples=len(samples), bnb_quotes=len(prices), failures=len(failures)),
                  symbols=detail,
                  parameters=dict(min_samples=min_samples, min_samples_scope='per token and regime',
                                  min_days=min_days, require_weekend=require_weekend,
                                  session_calendar_sha256=hashlib.sha256(raw).hexdigest(),
                                  regimes='US_SESSION inside a calendar session, else OFF_SESSION; trading is 24/7',
                                  combine='per field, the worse of US_SESSION and OFF_SESSION',
                                  quote_ttl_seconds=quote_ttl_seconds, quote_ttl_seconds_source='KIT_STATED',
                                  fee_bps='0: fees are netted in quoted amounts',
                                  gas='p90 nearest rank, wei; swap = max(tx.gas, ceil(1.2 x estimate)) x gasPrice',
                                  impact='median of buy and sell priceImpactPercent x 100, ceiled, >= 1',
                                  spread='median(round trip - buy impact - sell impact), ceiled, >= 0',
                                  slippage='p90 of re-quote drift, ceiled, 1..50',
                                  token_open='openState per sample; counted, not filtered (F-95 guard is in code)'))
    return summary, report


def run_capture(market, out_dir, *, round_fn=capture_round, until=None, rounds=None, interval_seconds=600,
                now=lambda: datetime.now(timezone.utc), sleep=time.sleep, log=lambda line: None, **round_options):
    """Capture rounds until `until` (UTC ISO time) or for `rounds` rounds; returns how many ran.

    One file per UTC day (`capture-YYYY-MM-DD.jsonl`), appended round by round, so a stop loses at most the round in
    progress. An unexpected error in a round becomes a FAILURE record (stage ROUND) and the loop goes on (Q8, Q9).
    Invalid parameters and rejected credentials or region (FATAL_OUTCOMES) are recorded, then raised: no later round
    can succeed, and a silent multi-day loop would miss the weekend."""
    if (until is None) == (rounds is None):
        raise ContractError('Give exactly one of --until and --rounds')
    if interval_seconds < 0:
        raise ContractError('Invalid interval')
    end = None
    if until is not None:
        try:
            end = datetime.fromisoformat(until.replace('Z', '+00:00'))
        except ValueError:
            raise ContractError('--until must be an ISO time') from None
        if end.tzinfo is None:  # a naive time would silently be read as the host's local time
            raise ContractError('--until needs a UTC offset, e.g. 2026-10-19T00:00:00Z')
        end = end.astimezone(timezone.utc)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    done = 0
    while (now() < end) if end is not None else done < rounds:
        started = now()
        fatal = None
        try:
            records = round_fn(market, **round_options)
        except Exception as error:  # one bad round never ends a multi-day capture, unless no round can succeed
            fatal = error if _fatal(error) else None
            records = [dict(kind='FAILURE', symbol=None, stage='ROUND',
                            reason=str(error) if fatal else type(error).__name__,
                            at=started.isoformat(timespec='milliseconds').replace('+00:00', 'Z'))]
        path = out / f'capture-{started.date().isoformat()}.jsonl'
        with path.open('a', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, sort_keys=True) + '\n')
        done += 1
        log(f'{started.isoformat(timespec="seconds")} round {done}: '
            f'{sum(r.get("kind") == "SAMPLE" for r in records)} samples, '
            f'{sum(r.get("kind") == "FAILURE" for r in records)} failures -> {path.name}')
        if fatal is not None:
            raise fatal
        if (end is None and done < rounds) or (end is not None and now() < end):
            sleep(interval_seconds)
    return done


def read_captures(directory):
    records = []
    for path in sorted(Path(directory).glob('capture-*.jsonl')):
        for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except ValueError:
                    raise ContractError(f'{path.name}:{n} is not JSON') from None
    return records


# ---------------------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture', help='read-only quote capture (needs BINANCE_API_KEY / BINANCE_SECRET_KEY)')
    c.add_argument('--address', required=True, help='a public wallet address (quotes check no balance)')
    c.add_argument('--out-dir', required=True)
    c.add_argument('--rounds', type=int, help='run this many rounds (or use --until)')
    c.add_argument('--until', help='capture until this UTC time, e.g. 2026-10-19T00:00:00Z')
    c.add_argument('--interval-seconds', type=float, default=600)
    c.add_argument('--cash-units', type=int, default=40_000_000, help='quote size in USDT money units (6 decimals)')
    c.add_argument('--requote-seconds', type=float, default=15)
    c.add_argument('--fallback-gas-limit', type=int, default=FALLBACK_GAS_LIMIT)
    s = sub.add_parser('summarize', help='offline summary of every capture file in a directory')
    s.add_argument('--captures', required=True)
    s.add_argument('--output', required=True)
    s.add_argument('--min-samples', type=int, default=10)
    s.add_argument('--min-days', type=int, default=3)
    s.add_argument('--no-weekend-required', action='store_true')
    s.add_argument('--quote-ttl-seconds', type=int, default=QUOTE_TTL_SECONDS)
    s.add_argument('--session-calendar', default=str(SESSION_CALENDAR), help='frozen USRegularSessions.v1 file')
    args = parser.parse_args(argv)
    try:
        if args.command == 'capture':
            key, secret = os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_SECRET_KEY')
            if not key or not secret:
                print('BINANCE_API_KEY / BINANCE_SECRET_KEY are not set; nothing was called', file=sys.stderr)
                return 2
            from .web3 import Artifacts, Web3Client
            out = Path(args.out_dir)
            out.mkdir(parents=True, exist_ok=True)
            market = MarketPort(Web3Client(key, secret, artifacts=Artifacts(str(out / 'artifacts'))), args.address)
            rounds = args.rounds if args.rounds is not None or args.until else 1  # both together are refused
            run_capture(market, out, until=args.until, rounds=rounds,
                        interval_seconds=args.interval_seconds, log=lambda line: print(line, flush=True),
                        cash_units=args.cash_units, requote_seconds=args.requote_seconds,
                        fallback_gas_limit=args.fallback_gas_limit)
            return 0
        output = Path(args.output)
        report_path = output.with_name(output.stem + '.report.json')
        if output.exists() or report_path.exists():
            print(f'{output} or its report exists; a summary is never replaced', file=sys.stderr)
            return 2
        summary, report = summarize(read_captures(args.captures), min_samples=args.min_samples,
                                    min_days=args.min_days, require_weekend=not args.no_weekend_required,
                                    quote_ttl_seconds=args.quote_ttl_seconds, calendar=args.session_calendar)
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print('QuoteCostSummary.v1', summary['capture_hash'], '->', output)
        return 0
    except (ContractError, Unavailable) as refused:
        print('refused:', refused, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
