"""Render config/release/deviations.v1.json into plan.md §6.5 (IDEA-042 item 8, R3).

    python tools/render_deviations.py           # print the table
    python tools/render_deviations.py --write   # replace the marked block in docs/skill/larp/plan.md
    python tools/render_deviations.py --check   # exit 1 if plan.md differs from the register
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from larp.runtime.register import BEGIN, DEVIATIONS, END, render, resolver, validate_deviations  # noqa: E402

PLAN = ROOT / 'docs/skill/larp/plan.md'


def table():
    doc = json.loads((ROOT / DEVIATIONS).read_text(encoding='utf-8'))
    proposal = (ROOT / doc['proposal']).read_text(encoding='utf-8')
    return render(validate_deviations(doc, proposal, resolver(ROOT)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    text, plan = table(), PLAN.read_text(encoding='utf-8')
    if BEGIN not in plan or END not in plan:
        raise SystemExit('plan.md has no deviations block markers')
    start, end = plan.index(BEGIN), plan.index(END) + len(END)
    if args.check:
        return 0 if plan[start:end] == text else 1
    if args.write:
        PLAN.write_text(plan[:start] + text + plan[end:], encoding='utf-8')
        return 0
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
