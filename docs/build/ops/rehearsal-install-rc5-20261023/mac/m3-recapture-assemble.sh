#!/bin/bash
# M3 (Mac, Yao): pre-install recapture and signer.json assembly for RC5 and the new run (IDEA-049-C SJ-10).
# Read-only on primary: the reviewed LD10 probe (sha256 692787e4..., regenerated here from the release checkout; the
# probe tool is byte-identical between RC4 and RC5) reads run 1's /etc/larp/runtime.json and /opt/larp/current, so run
# this BEFORE r1/p2 change primary.
# Capture -> review -> assemble back to back (quotes older than 300 s are refused). Prints no private value.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to run 1 RC4 bindings (rehearsal-install-20261022/private/bindings-d03bbb1.json)}
PROBE_SHA=692787e49a55c37fec5af9082a0247e202e86f4aaf8e083e939c55c6d59b69b3
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" /opt/homebrew/bin/python3.12 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261022'
assert b['database_name'] == 'larp_rehearsal1' and b['build_id'] == 'd03bbb16cf51277c73d7f381b08f9551d0c10415'
# SJ-10: the new run changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261023', database_name='larp_rehearsal2')
fd = os.open(os.environ['NEW'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump(b, f, sort_keys=True)
print('bindings written for build', b['build_id'][:7])
PY
fi
"$PY" -I "$WT/tools/deploy/ld10_readonly_packet.py" --profile "$WT/docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json" \
  --output "$P/capture-$STAMP.sh" >/dev/null
[[ $(shasum -a 256 "$P/capture-$STAMP.sh" | cut -c1-64) == "$PROBE_SHA" ]] || { echo "probe differs from the reviewed one"; exit 3; }
cp "$P/capture-$STAMP.sh" "$HERE/host/capture.sh"
/opt/homebrew/bin/python3.12 -I "$HERE/ssm_run.py" "$HERE/host/capture.sh" > /dev/null
rm -f "$HERE/host/capture.sh"
cd "$WT"
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/capture-stdout.txt" --bindings "$B" \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 2000000 \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
