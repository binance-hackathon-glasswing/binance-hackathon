#!/bin/bash
# M3 (Mac, Yao): pre-install recapture and signer.json assembly for run 5 on S4 (IDEA-097).
# Read-only on primary: the LD10 probe for the S4 profile e79a92fc... (sha256 9397c0cf..., regenerated here from the
# release checkout) reads run 4's /etc/larp/runtime.json and /opt/larp/current, so run this BEFORE r1/p2 change
# primary, and only after the BNB top-up (the S4 exit reserve is 0.01536 BNB with allowance recovery).
# Capture -> review -> assemble back to back (quotes older than 300 s are refused). Prints no private value.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to run 4 RC7 bindings (rehearsal-install-rc7-20261024/private/bindings-2d16007.json)}
PROBE_SHA=9397c0cfdcce2982eaaecab6359eb53464fad64127fa7112f4ed99ae2eecb63f
PROFILE=docs/build/evidence/s4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" /opt/homebrew/bin/python3.12 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261024-s2'
assert b['database_name'] == 'larp_rehearsal4' and b['build_id'] == '2d160073d0f26c1f35c6c977c3dd6167a5ee0d26'
# IDEA-097: run 5 changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261025-s4', database_name='larp_rehearsal5')
fd = os.open(os.environ['NEW'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump(b, f, sort_keys=True)
print('bindings written for build', b['build_id'][:7])
PY
fi
"$PY" -I "$WT/tools/deploy/ld10_readonly_packet.py" --profile "$WT/$PROFILE" \
  --output "$P/capture-$STAMP.sh" >/dev/null
[[ $(shasum -a 256 "$P/capture-$STAMP.sh" | cut -c1-64) == "$PROBE_SHA" ]] || { echo "probe differs from the reviewed one"; exit 3; }
cp "$P/capture-$STAMP.sh" "$HERE/host/capture.sh"
/opt/homebrew/bin/python3.12 -I "$HERE/ssm_run.py" "$HERE/host/capture.sh" > /dev/null
rm -f "$HERE/host/capture.sh"
cd "$WT"
# IDEA-097: the source ledger is run 4, which holds GOOGLB/NVDAB/SKHYB/TSLAB, so every stock must MATCH the chain
# exactly and becomes run 5's starting book. --allowance-recovery (IDEA-096): run 4's leftover SKHYB router allowance
# is accepted because execution and the signer policy opt into zero-only recovery, and run 5 clears it itself.
# BNB may exceed the ledger (the top-up); the review then needs it to cover the 0.01536 BNB exit reserve.
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/capture-stdout.txt" --bindings "$B" \
  --profile "$WT/$PROFILE" --allowance-recovery \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 0 \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
