# P3 (primary, host mutation): install the hash-checked M4 package and run the offline checks. Starts nothing.
#   p3-install-primary.sh <bucket> <prefix> name=sha256 ...   (the exact command M4 prints)
set -euo pipefail
BUCKET=$1; PREFIX=$2; shift 2
declare -A want; for kv in "$@"; do want[${kv%%=*}]=${kv#*=}; done
for n in release.json runtime.json uploader.json operations.json execution.json strategy-profile.json \
         session-calendar.json initial-state.json evidence.env registration-evidence.json untrusted-router-policy.json \
         token-history.json model-routing.json; do
  [[ -n ${want[$n]:-} ]] || { echo "missing hash for $n"; exit 3; }
  [[ ! -e /etc/larp/$n ]] || { echo "/etc/larp/$n exists; not overwriting"; exit 3; }
done
W=$(mktemp -d /root/pkg.XXXXXX); trap 'rm -rf "$W"' EXIT
for n in "${!want[@]}"; do
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX$n" "$W/$n"
  [[ $(sha256sum "$W/$n" | cut -d' ' -f1) == "${want[$n]}" ]] || { echo "$n hash differs"; exit 3; }
done
BUILD=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['build_id'])" "$W/runtime.json")
readlink -f /opt/larp/current | grep -q "$BUILD" || { echo "installed release is not $BUILD; run p2"; exit 3; }
install -m 0640 -o root -g larp-evidence "$W/runtime.json" /etc/larp/runtime.json
install -m 0640 -o root -g larp-uploader "$W/uploader.json" /etc/larp/uploader.json
install -m 0640 -o root -g larp-archive "$W/operations.json" /etc/larp/operations.json
install -m 0640 -o root -g larp-execution "$W/execution.json" /etc/larp/execution.json
for n in release.json strategy-profile.json session-calendar.json initial-state.json evidence.env \
         registration-evidence.json untrusted-router-policy.json token-history.json model-routing.json; do
  install -m 0644 -o root -g root "$W/$n" "/etc/larp/$n"
done
(cd /etc/larp && sha256sum release.json runtime.json uploader.json operations.json execution.json strategy-profile.json \
  session-calendar.json initial-state.json evidence.env registration-evidence.json untrusted-router-policy.json \
  token-history.json model-routing.json rds-ca.pem)
cd /opt/larp/current
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
$P -m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current --profile host \
  --config /etc/larp/operations.json --runtime-config /etc/larp/runtime.json \
  --service-config uploader=/etc/larp/uploader.json --service-config execution=/etc/larp/execution.json
runuser -u larp-runtime -g larp-runtime -G larp-evidence -- $P -m larp.runtime.service check --config /etc/larp/runtime.json \
  --manifest /etc/larp/release.json --root /opt/larp/current
runuser -u larp-execution -- $P -m larp.execution_live.main check --config /etc/larp/execution.json \
  --manifest /etc/larp/release.json --root /opt/larp/current
# IDEA-089 S2-10: the runtime's quote verifier loads the router policy as larp-runtime; without a readable, matching
# file the runtime refuses to start (and without the pair it would trade like run 3: no executable quote).
runuser -u larp-runtime -g larp-runtime -G larp-evidence -- $P -I -c 'import hashlib, json, sys
d = json.load(open(sys.argv[1]))["driver"]
path, sha = d.get("untrusted_router_policy_file"), d.get("untrusted_router_policy_sha256")
if not path or not sha:
    sys.exit("runtime.json has no untrusted-router policy pair (S2-10)")
if hashlib.sha256(open(path, "rb").read()).hexdigest() != sha:
    sys.exit("router policy differs from runtime.json pin")
print("runtime_router_policy readable_by=larp-runtime sha256=" + sha[:8])' /etc/larp/runtime.json
# IDEA-103 / IDEA-104 R2: S5, like FS1, refuses to start without the pinned token history readable by larp-runtime.
runuser -u larp-runtime -g larp-runtime -G larp-evidence -- $P -I -c 'import hashlib, json, sys
d = json.load(open(sys.argv[1]))["driver"]
path, sha = d.get("token_history_file"), d.get("token_history_sha256")
if path != "/etc/larp/token-history.json" or not sha:
    sys.exit("runtime.json has no token history pin (IDEA-103)")
if hashlib.sha256(open(path, "rb").read()).hexdigest() != sha:
    sys.exit("token history differs from runtime.json pin")
print("runtime_token_history readable_by=larp-runtime sha256=" + sha[:8])' /etc/larp/runtime.json
# IDEA-104 R3: FS1 routing, readable by larp-runtime at its pin (FS1 sheet P2-P3).
runuser -u larp-runtime -g larp-runtime -G larp-evidence -- $P -I -c 'import hashlib, json, sys
d = json.load(open(sys.argv[1]))["driver"]
if d.get("assessor") != "aiand_routed" or d.get("model_routing_file") != "/etc/larp/model-routing.json":
    sys.exit("runtime.json is not the routed S5 runtime (IDEA-104 R3)")
if hashlib.sha256(open(d["model_routing_file"], "rb").read()).hexdigest() != d["model_routing_sha256"]:
    sys.exit("model routing differs from runtime.json pin")
print("runtime_model_routing readable_by=larp-runtime sha256=" + d["model_routing_sha256"][:8])' /etc/larp/runtime.json
install -d -m 0700 /root/rehearsal-evidence
R=/root/rehearsal-evidence/routes-primary-$(date -u +%Y%m%dT%H%M%SZ).json
# The report goes to the file only (it names every destination host, including the database endpoint).
if $P -m larp.runtime.routes --role primary --config runtime=/etc/larp/runtime.json --config uploader=/etc/larp/uploader.json \
     --config operations=/etc/larp/operations.json --config execution=/etc/larp/execution.json --root /opt/larp/current \
     --output "$R" > /dev/null; then
  echo "routes PASS $(sha256sum "$R" | cut -d' ' -f1) destinations=$(grep -c '"status"' "$R" || true)"
else
  echo "routes FAILED; report kept at $R on the host"; exit 5
fi
chronyc tracking | grep -E 'Reference ID|Stratum|System time|Leap status'
echo P3_DONE
