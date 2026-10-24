"""RV120-RV01: offline BUY-output drift counts; no executed-revert inference."""
import argparse
import hashlib
import json
from pathlib import Path

from larp.marketdata import cost_summary as cs
from larp.runtime.driver import SessionCalendar


def analyse(directory):
    files = sorted(Path(directory).glob('capture-*.jsonl'))
    if len(files) != 4:
        raise ValueError('The four completed DC-01 daily files are required')
    rows = [json.loads(line) for path in files for line in path.read_text().splitlines()]
    samples = [row for row in rows if row['kind'] == 'SAMPLE']
    calendar = Path(cs.SESSION_CALENDAR).read_bytes()
    sessions = SessionCalendar(json.loads(calendar)).sessions
    result = {}
    for symbol in sorted({row['symbol'] for row in samples}):
        result[symbol] = {}
        for regime in ('US_SESSION', 'OFF_SESSION'):
            selected = [row for row in samples if row['symbol'] == symbol
                        and cs._regime(row['at'], sessions) == regime]
            absolute = adverse = favourable = 0
            for row in selected:
                before, after = int(row['buy_received']), int(row['requote_received'])
                if before <= 0 or after <= 0:
                    raise ValueError('Positive quoted BUY outputs required')
                delta = (before - after) * 10000
                absolute += abs(delta) > 8 * before
                adverse += delta > 8 * before
                favourable += -delta > 8 * before
            if absolute != adverse + favourable or not selected:
                raise ValueError('Directional partition or regime coverage differs')
            result[symbol][regime] = dict(
                samples=len(selected), absolute_exceedances=absolute,
                adverse_exceedances=adverse, favourable_exceedances=favourable,
                absolute_percent=round(100 * absolute / len(selected), 6),
                adverse_percent=round(100 * adverse / len(selected), 6),
                favourable_percent=round(100 * favourable / len(selected), 6))
    return dict(schema='DirectionalRequoteDriftReview.v1', decision_id='IDEA-063 RV120-RV01',
                threshold_bps=8, comparison='strictly greater; exact integer cross multiplication',
                adverse_definition='later BUY quote receives fewer token units than the initial BUY quote',
                interpretation='Counterfactual quote-output comparisons, not executed or simulated reverts.',
                samples=len(samples),
                input_files={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
                calendar_sha256=hashlib.sha256(calendar).hexdigest(), symbols=result,
                changes_selected_profile=False, actual_revert_frequency=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyse(args.capture), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
