# M3: source-run8 read-only capture, fresh coverage and run8r2 signer candidate.
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/pins.sh"
MAIN=${LARP_REPO:?set LARP_REPO to the canonical repository checkout}
WT=$MAIN/.claude/worktrees/release-${BUILD:0:7}
PY=${LARP_PY:?set LARP_PY to a Python 3.12 venv built from requirements.lock}
OLD_BINDINGS=${OLD_BINDINGS:?set OLD_BINDINGS to source run 8 bindings (the original run8 bindings file)}
# Historical S5R2-8 exact-surplus accounting; no funding transfer is planned (TOPUP defaults to zero).
TOPUP=0; [[ $TOPUP =~ ^[0-9]+$ ]] || { echo "TOPUP must be whole micro-USDT"; exit 3; }
PROBE_SHA=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["probe_sha256"])' "$HERE/package.json")
PROFILE=$HERE/inputs/rehearsal-s5-next.json
[[ -d $WT ]] || git -C "$MAIN" worktree add --detach "$WT" "$BUILD" >/dev/null
[[ $(git -C "$WT" rev-parse HEAD) == "$BUILD" && -z $(git -C "$WT" status --porcelain) ]] || { echo "release checkout not clean $BUILD"; exit 3; }
P=$HERE/private; install -d -m 0700 "$P"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
B=$P/bindings-${BUILD:0:7}.json
if [[ ! -f $B ]]; then
  OLD="$OLD_BINDINGS" NEW="$B" BUILD="$BUILD" python3 -I - <<'PY'
import json, os
b = json.loads(open(os.environ['OLD']).read())
assert b['schema'] == 'RehearsalSignerBindings.v1' and b['run_id'] == 'larp-dev-rehearsal-20261027-s5-small'
assert b['database_name'] == 'larp_rehearsal8' and b['build_id'] == 'bdd515f80dbc57e80ffeb60c6001091d6e1d7c08'
# IDEA-104: run 8 changes exactly these three bindings; everything else (CA, host, region, router policy) stays.
b.update(build_id=os.environ['BUILD'], run_id='larp-dev-rehearsal-20261027-s5-small-r2', database_name='larp_rehearsal8r2')
fd = os.open(os.environ['NEW'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump(b, f, sort_keys=True)
print('bindings written for build', b['build_id'][:7])
PY
fi
"$PY" -I "$WT/tools/deploy/ld10_readonly_packet.py" --profile "$PROFILE" \
  --output "$P/capture-$STAMP.sh" >/dev/null
[[ $(shasum -a 256 "$P/capture-$STAMP.sh" | cut -c1-64) == "$PROBE_SHA" ]] || { echo "probe differs from the reviewed one"; exit 3; }
cp "$P/capture-$STAMP.sh" "$HERE/host/capture.sh"
python3 -I "$HERE/ssm_run.py" "$HERE/host/capture.sh" > /dev/null
rm -f "$HERE/host/capture.sh"
cd "$WT"
# Recovery permits inherited allowances; positive reservations or pending executions still refuse.
"$PY" -m tools.deploy.review_rehearsal_caps --packet "$HERE/results/primary-capture-stdout.txt" --bindings "$B" \
  --profile "$PROFILE" --allowance-recovery \
  --output-dir "$P/review-$STAMP" --signer-out "$P/signer-$STAMP" --accept-usdt-deficit-units 0 \
  --accept-usdt-surplus-units "$TOPUP" \
  | tee "$P/assembly-$STAMP.json"
echo "M3 stamp $STAMP (signer candidate in private/signer-$STAMP)"
