#!/usr/bin/env bash
# IDEA-047 H02: provision a release bundle in an Amazon Linux 2023 container with networking off, twice per role,
# then check the result. The container adds tar/gzip/useradd/find at image build (the AMI ships them); provisioning
# itself runs with --network none, as on the signer host. No systemd in a container: units are installed, not enabled.
#
#   tools/test_host_bundle.sh <larp-BUILD-ARCH.tar.gz> [linux/amd64|linux/arm64]
set -euo pipefail
[[ $# -ge 1 ]] || { echo "usage: $0 <bundle.tar.gz> [platform]" >&2; exit 2; }
bundle=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
platform=${2:-}
image=larp-host-test:al2023
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

docker build -q ${platform:+--platform "$platform"} -t "$image" - >/dev/null <<'EOF'
FROM amazonlinux:2023@sha256:8ed3c0a996841537f75607e7d1de2114d8150391f75792e8da9268738547e73f
RUN dnf install -y -q tar gzip shadow-utils findutils && dnf clean all
EOF

cat > "$work/checks.sh" <<'EOF'
set -euo pipefail
role=$1
fail() { echo "FAIL[$role]: $*" >&2; exit 1; }
cd /tmp
tar -xzf /bundle.tar.gz --wildcards '*/provision.sh' '*/BUNDLE.env'
provision=$(ls /tmp/larp-*/provision.sh)
build=$(grep '^build_id=' /tmp/larp-*/BUNDLE.env | cut -d= -f2)
bash "$provision" "$role" /bundle.tar.gz --no-systemctl
bash "$provision" "$role" /bundle.tar.gz --no-systemctl  # idempotent
[[ $(readlink /opt/larp/current) == /opt/larp/releases/$build ]] || fail "current link"
py=/opt/larp/current/.venv/bin/python
[[ $($py -c 'import platform; print(platform.python_version())') == 3.12.15 ]] || fail "python version"
$py -c 'import eth_account, psycopg, boto3, rlp' || fail "imports"
$py -m pip check >/dev/null || fail "pip check"
for module in larp.signer.service larp.execution_live.main larp.audit.service larp.runtime.service \
              larp.runtime.operations larp.runtime.preflight larp.sources.live; do
  (cd /opt/larp/current && $py -m "$module" --help >/dev/null) || fail "entry point $module"
done
[[ -z $(find /opt/larp ! -user root) ]] || fail "non-root files under /opt/larp"
[[ -z $(find /opt/larp/releases /opt/larp/python -perm -o+w ! -type l) ]] || fail "world-writable files"
[[ $(stat -c %a /etc/larp) == 755 && $(stat -c %U /etc/larp) == root ]] || fail "/etc/larp mode"
[[ $(stat -c %a /etc/larp/role-$role) == 444 ]] || fail "role marker"
[[ -s /etc/larp/rds-ca.pem ]] || fail "rds ca"
units=$(ls /etc/systemd/system | sort | tr '\n' ' ')
if [[ $role == signer ]]; then
  id larp-signer >/dev/null || fail "signer user"
  ! id larp-runtime >/dev/null 2>&1 || fail "primary user on signer"
  [[ $units == "larp-signer.service " ]] || fail "units: $units"
  [[ $(stat -c '%a %U' /etc/larp/signer) == '700 root' ]] || fail "/etc/larp/signer mode"
  # The key file: root-only; the service user cannot read it directly, only through a credential copy.
  $py -c 'from eth_account import Account; print(Account.create().key.hex())' > /etc/larp/signer/wallet.key
  chmod 0600 /etc/larp/signer/wallet.key
  uid=$(id -u larp-signer); gid=$(id -g larp-signer)
  load='import sys; from larp.signer.keyfile import load_key_file; print(sorted(load_key_file(sys.argv[1])))'
  (cd /opt/larp/current && $py -c "$load" /etc/larp/signer/wallet.key) | grep -q WALLET_PRIVATE_KEY || fail "root load"
  as_signer="import os,sys; os.setgroups([]); os.setgid($gid); os.setuid($uid); exec(sys.argv[2])"
  if (cd /opt/larp/current && $py -c "$as_signer" /etc/larp/signer/wallet.key "$load" 2>/dev/null); then
    fail "service user read the root-only key"
  fi
  credentials=/run/credentials/larp-signer.service
  install -d -m 0500 -o larp-signer -g larp-signer "$credentials"
  install -m 0400 -o larp-signer -g larp-signer /etc/larp/signer/wallet.key "$credentials/wallet.key"
  out=$(cd /opt/larp/current && $py -c "import sys; sys.argv=sys.argv[:1]+sys.argv[2:]; $as_signer" \
        _ "$credentials/wallet.key" "$load") || fail "credential load"
  [[ $out == *WALLET_PRIVATE_KEY* ]] || fail "credential content"
  chmod 0440 "$credentials/wallet.key"
  ! (cd /opt/larp/current && $py -c "import sys; sys.argv=sys.argv[:1]+sys.argv[2:]; $as_signer" \
     _ "$credentials/wallet.key" "$load" 2>/dev/null) || fail "group-readable credential accepted"
  rm -rf /etc/larp/signer/wallet.key "$credentials"
else
  for user in larp-runtime larp-execution larp-uploader larp-evidence larp-archive; do
    id "$user" >/dev/null || fail "user $user"
  done
  ! id larp-signer >/dev/null 2>&1 || fail "signer user on primary"
  expected="larp-archive.service larp-archive.timer larp-evidence.service larp-execution.service larp-runtime.service larp-uploader.service "
  [[ $units == "$expected" ]] || fail "units: $units"
  [[ ! -e /etc/larp/signer ]] || fail "signer key directory on primary"
fi
# The other role is refused on this host.
other=$([[ $role == signer ]] && echo primary || echo signer)
! bash "$provision" "$other" /bundle.tar.gz --no-systemctl >/dev/null 2>&1 || fail "other role accepted"
# A tampered bundle is refused before anything is installed.
mkdir -p /tmp/tamper && tar -xzf /bundle.tar.gz -C /tmp/tamper
echo '# tampered' >> /tmp/tamper/larp-*/release/larp/__init__.py
tar -czf /tmp/tampered.tar.gz -C /tmp/tamper .
! bash "$provision" "$role" /tmp/tampered.tar.gz --no-systemctl >/dev/null 2>&1 || fail "tampered bundle accepted"
echo "PASS[$role]: build $build, units: $units"
EOF

for role in primary signer; do
  docker run --rm --network none ${platform:+--platform "$platform"} \
    -v "$bundle:/bundle.tar.gz:ro" -v "$work/checks.sh:/checks.sh:ro" "$image" bash /checks.sh "$role"
done
