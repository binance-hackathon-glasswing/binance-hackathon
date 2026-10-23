#!/bin/bash
# M3 (Mac, Yao): pre-install recapture and signer.json assembly for RC6 and run 3 on S1 (IDEA-049-C SJ-11).
# Read-only on primary: the LD10 probe for the run-3 S1 profile 6bcf1dfb... (sha256 75547c8e..., regenerated here from
# the release checkout; it differs from the reviewed equal-weight probe 692787e4... only in the embedded profile line,
# SJ-11-RH01-P1) reads run 2's /etc/larp/runtime.json and /opt/larp/current, so run this BEFORE r1/p2 change primary.
# Capture -> review -> assemble back to back (quotes older than 300 s are refused). Prints no private value.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to run 2 RC5 bindings (rehearsal-install-rc5-20261023/private/bindings-d53d1b7.json)}
PROBE_SHA=75547c8e7d3d02e977e9859665f713580f64cc935f41641a3c129edc68fd9b99
PROFILE=docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" /opt/homebrew/bin/python3.12 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261023'
assert b['database_name'] == 'larp_rehearsal2' and b['build_id'] == 'd53d1b7aa8f18790f0bdde73cfdcdbed95555043'
# SJ-11: run 3 changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261024', database_name='larp_rehearsal3')
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
# SJ-11: the source ledger is run 2, which started from the chain holdings (96 USDT) and cannot have entered on RC5 (no
# basis verifier, SJ-10), so USDT, BNB and every stock must MATCH exactly; gate_a refuses a wallet holding stocks (C4).
# --profile: review against the S1 profile the probe carried (SJ-11-RH01), not the equal-weight default.
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/capture-stdout.txt" --bindings "$B" \
  --profile "$WT/$PROFILE" \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 0 \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
