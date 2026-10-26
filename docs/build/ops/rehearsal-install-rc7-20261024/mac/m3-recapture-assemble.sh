#!/bin/bash
# M3 (Mac, Yao): pre-install recapture and signer.json assembly for RC7 and run 4 on S2 (IDEA-089 S2-7).
# Read-only on primary: the LD10 probe for the run-4 S2 profile eb55d76a... (sha256 8e8d6c89..., regenerated here from
# the release checkout; it differs from run 3's reviewed probe 75547c8e... only in the embedded profile line) reads
# run 3's /etc/larp/runtime.json and /opt/larp/current, so run this BEFORE r1/p2 change primary. The review uses S2's
# sizes, which are run 3's (19 USDT per buy).
# Capture -> review -> assemble back to back (quotes older than 300 s are refused). Prints no private value.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to run 3 RC6 bindings (rehearsal-install-rc6-20261023/private/bindings-9dc5eda.json)}
PROBE_SHA=8e8d6c89bf4f16e69465b2fc46db4414b4b623d2d6909b2a3c9325d5930ce97a
PROFILE=docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" /opt/homebrew/bin/python3.12 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261024'
assert b['database_name'] == 'larp_rehearsal3' and b['build_id'] == '9dc5edab61b6bffdb3c75cc4d498bb651a91ba43'
# IDEA-089 S2-7: run 4 changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261024-s2', database_name='larp_rehearsal4')
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
# IDEA-089: the source ledger is run 3, which started from the chain holdings (96 USDT) and could not place an order
# on RC6 (no quote verifier, SJ-11-QV01), so USDT, BNB and every stock must MATCH exactly; gate_a refuses a wallet
# holding stocks (C4). --profile: review against the S2 profile the probe carried, not the equal-weight default.
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/capture-stdout.txt" --bindings "$B" \
  --profile "$WT/$PROFILE" \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 0 \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
