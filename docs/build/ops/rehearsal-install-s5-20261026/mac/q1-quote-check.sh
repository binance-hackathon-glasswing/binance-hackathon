#!/bin/bash
# Q1 (Mac, read-only; IDEA-089 S2-6 and S2-12; supplementary for S5, as in the FS1 sheet): shortly before install, one live quote per S2 name and side through the
# service's own verifier (tools/deploy/quote_check.py, IDEA-088 A1): BUY at the S2 size (19 USDT) and SELL of the
# token units a fresh BUY quote returns (hypothetical, not holdings). The tool pins run 3's profile 6bcf1dfb...; the S2
# profile eb55d76a... differs from it only in s1.execution hours/attempts, the window and policy_id, which the quote
# port, the verifier and _quote_at_cap do not read (tests/runtime/test_run4_sheet.py), so the verdict is S2's. S5 uses 20 bp, not run 3's 8 bp: a PASS here is not an S5-pinned
# quote (the FS1 sheet's Q1 note); M3's caps review at the S5 profile is the binding check.
# No signer, AWS, database or submit path. Raw responses stay in private/; stdout carries public values only.
#   LARP_PY=<venv python> bash mac/q1-quote-check.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
OUT=$HERE/private/quote-check-$(date -u +%Y%m%dT%H%M%SZ); install -d -m 0700 "$OUT"
R=$HERE/results; install -d "$R"
fail=0
for s in GOOGLB MSFTB NVDAB SKHYB TSLAB; do
  for side in BUY SELL; do
    code=0
    (cd "$WT" && "$PY" -m tools.deploy.quote_check --symbol "$s" --side "$side" --env-file "$MAIN/.env" \
      --out "$OUT/$s-$side") > "$R/q1-$s-$side.json" || code=$?
    "$PY" -I -c 'import json, sys
r = json.load(open(sys.argv[1]))
print(sys.argv[2], r.get("status"), "token_open=%s underlying_open=%s" % (r.get("token_open"), r.get("underlying_open")),
      "impact_bps=%s" % r.get("impact_bps"), "quote_at_cap=%s" % (r.get("quote_at_cap") or {}).get("accepted"),
      "exit=" + sys.argv[3])' "$R/q1-$s-$side.json" "$s $side" "$code"
    [[ $code == 0 ]] || fail=1
  done
done
date -u +"checked_at %Y-%m-%dT%H:%M:%SZ"
# S2-6: every name must be VERIFIED_EXECUTABLE with quote_at_cap accepted, for BUY and SELL. A refusal is a finding to
# record in IDEA-089, never a reason to bypass the check.
[[ $fail == 0 ]] || { echo "a quote was refused; record it and stop (no Q1_DONE)"; exit 5; }
echo Q1_DONE
