# S1 (signer, host mutation, after T1 Terraform access and P2 on the signer): install signer.json, the router policy
# and the SAME bound release.json primary installed, then run the offline checks and the SA4 route check. No key yet.
#   s1-install-signer.sh <bucket> <prefix> release.json=sha signer.json=sha untrusted-router-policy.json=sha
set -euo pipefail
BUCKET=$1; PREFIX=$2; shift 2
declare -A want; for kv in "$@"; do want[${kv%%=*}]=${kv#*=}; done
[[ -e /etc/larp/role-signer ]] || { echo "not provisioned as signer; run p2 signer first"; exit 3; }
for n in release.json signer.json untrusted-router-policy.json; do
  [[ -n ${want[$n]:-} ]] || { echo "missing hash for $n"; exit 3; }
  [[ ! -e /etc/larp/$n ]] || { echo "/etc/larp/$n exists; not overwriting"; exit 3; }
done
W=$(mktemp -d /root/pkg.XXXXXX); trap 'rm -rf "$W"' EXIT
for n in release.json signer.json untrusted-router-policy.json; do
  aws s3 cp --only-show-errors "s3://$BUCKET/$PREFIX$n" "$W/$n"
  [[ $(sha256sum "$W/$n" | cut -d' ' -f1) == "${want[$n]}" ]] || { echo "$n hash differs"; exit 3; }
done
BUILD=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['build_id'])" "$W/signer.json")
readlink -f /opt/larp/current | grep -q "$BUILD" || { echo "installed release is not $BUILD; run p2"; exit 3; }
install -m 0640 -o root -g larp-signer "$W/signer.json" /etc/larp/signer.json
install -m 0644 -o root -g root "$W/release.json" /etc/larp/release.json
install -m 0644 -o root -g root "$W/untrusted-router-policy.json" /etc/larp/untrusted-router-policy.json
(cd /etc/larp && sha256sum release.json signer.json untrusted-router-policy.json rds-ca.pem)
stat -c '%a %U:%G %n' /etc/larp/signer
cd /opt/larp/current
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
$P -m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current --profile host \
  --service-config signer=/etc/larp/signer.json
runuser -u larp-signer -- $P -m larp.signer.service check --config /etc/larp/signer.json \
  --manifest /etc/larp/release.json --root /opt/larp/current
install -d -m 0700 /root/rehearsal-evidence
R=/root/rehearsal-evidence/routes-signer-$(date -u +%Y%m%dT%H%M%SZ).json
# SA4 (IDEA-080): with the SSM endpoints up, the signer still has no internet route. Report to the file only.
if $P -m larp.runtime.routes --role signer --config signer=/etc/larp/signer.json --root /opt/larp/current \
     --output "$R" > /dev/null; then
  echo "routes PASS $(sha256sum "$R" | cut -d' ' -f1) destinations=$(grep -c '"status"' "$R" || true)"
else
  echo "routes FAILED; report kept at $R on the host"; exit 5
fi
chronyc tracking | grep -E 'Reference ID|Stratum|System time|Leap status'
echo S1_DONE
