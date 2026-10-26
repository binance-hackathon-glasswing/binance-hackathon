#!/bin/bash
# M3 (Mac, Yao): pre-install recapture and signer.json assembly for run 7 on S5 (IDEA-104 R2).
# Read-only on primary: the LD10 probe for the S5 profile 6dadc196... (sha256 68e49922..., regenerated here from the
# release checkout) reads run 6's /etc/larp/runtime.json and /opt/larp/current, so run this BEFORE r1/p2 change
# primary, after S5-SIZE01 source validation (B0; no top-up). The exit reserve is
# 0.01536 BNB with allowance recovery.
# Capture -> review -> assemble back to back (quotes older than 300 s are refused). Prints no private value.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
MAIN=/Users/songyaozhu/binance-hackathon
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to run 6 bindings (rehearsal-install-s4b-20261026/private/bindings-7fc9f60.json)}
# Historical S5R2-8 exact-surplus accounting; no funding transfer is planned (TOPUP defaults to zero).
TOPUP=${TOPUP:-0}; [[ $TOPUP =~ ^[0-9]+$ ]] || { echo "TOPUP must be whole micro-USDT"; exit 3; }
PROBE_SHA=68e49922432f8a8e8081fbaa32b3d8bb3b5614a5ca2982b6ed5ee671262f8e17
PROFILE=docs/build/evidence/s5-rehearsal-profile-20261026/rehearsal-s5.json
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" /opt/homebrew/bin/python3.12 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261026-s4b'
assert b['database_name'] == 'larp_rehearsal6' and b['build_id'] == '7fc9f6019b54dccaf13b886c2e1123e703abf67a'
# IDEA-104: run 7 changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261026-s5', database_name='larp_rehearsal7')
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
# IDEA-104: the source ledger is run 6, which ended flat (every stock 0, every router allowance 0), so the chain must
# MATCH it with no stock. --allowance-recovery (IDEA-096): S5 is FS1-R with recovery; execution and the signer policy
# opt into zero-only recovery. USDT may exceed the ledger (the B0 top-up); BNB must cover the 0.01536 BNB exit reserve.
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/capture-stdout.txt" --bindings "$B" \
  --profile "$WT/$PROFILE" --allowance-recovery \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 0 \
  --accept-usdt-surplus-units "$TOPUP" \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
