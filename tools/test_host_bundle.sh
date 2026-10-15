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
sha=$(sha256sum /bundle.tar.gz | cut -d' ' -f1)
# IDEA-047 R6: the bundle must match the CI-recorded hash; a missing, malformed or different hash is refused first.
! bash "$provision" "$role" /bundle.tar.gz --no-systemctl >/dev/null 2>&1 || fail "missing hash accepted"
! bash "$provision" "$role" /bundle.tar.gz --expect-sha256 "${sha^^}" --no-systemctl >/dev/null 2>&1 \
  || fail "malformed hash accepted"
! bash "$provision" "$role" /bundle.tar.gz --expect-sha256 "$(printf '0%.0s' {1..64})" --no-systemctl >/dev/null 2>&1 \
  || fail "different hash accepted"
[[ ! -e /opt/larp ]] || fail "a refused hash installed something"
bash "$provision" "$role" /bundle.tar.gz --expect-sha256 "$sha" --no-systemctl
bash "$provision" "$role" /bundle.tar.gz --expect-sha256 "$sha" --no-systemctl  # idempotent
[[ $(readlink /opt/larp/current) == /opt/larp/releases/$build ]] || fail "current link"
py=/opt/larp/current/.venv/bin/python
[[ $($py -c 'import platform; print(platform.python_version())') == 3.12.15 ]] || fail "python version"
$py -c 'import eth_account, psycopg, boto3, rlp' || fail "imports"
$py -m pip check >/dev/null || fail "pip check"
for module in larp.signer.service larp.execution_live.main larp.audit.service larp.runtime.service \
              larp.runtime.operations larp.runtime.preflight larp.sources.live; do
  (cd /opt/larp/current && $py -m "$module" --help >/dev/null) || fail "entry point $module"
done
# R8 and #62 item 3: bind the CI-built manifest on the packaged release with synthetic registration evidence, then
# run startup preflight against the bound manifest. No service starts.
ci=/opt/larp/current/release-manifest.json
[[ $(stat -c '%a %U' "$ci") == '444 root' ]] || fail "CI release manifest mode"
(cd /opt/larp/current && $py - <<'PY'
import json
from pathlib import Path
from larp.contracts import Document
ci = Document(Path('release-manifest.json').read_bytes()).read()
assert ci['build_id'] == Path.cwd().resolve().name, 'CI manifest is for another build'
Path('/tmp/registration.json').write_text(json.dumps(dict(schema='RegistrationEvidence.v1',
    evidence_ref='synthetic-only', build_id=ci['build_id'], repository=ci['repository'])))
PY
) || fail "CI release manifest unreadable"
(cd /opt/larp/current && $py -m larp.runtime.preflight --bind "$ci" --root /opt/larp/current \
  --registration-evidence /tmp/registration.json --build-output /tmp/bound-release.json >/dev/null) \
  || fail "binding the CI release manifest"
(cd /opt/larp/current && $py -m larp.runtime.preflight --manifest /tmp/bound-release.json \
  --root /opt/larp/current --profile host) || fail "packaged release preflight"
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
  # IDEA-047 R3/R15: the poller uses DELETE journaling; runtime readers never create WAL sidecars.
  # reads it read-only through the larp-evidence group, and nobody else can open it.
  state=/var/lib/larp-evidence
  install -d -m 0770 -o larp-evidence -g larp-evidence "$state"
  ev_uid=$(id -u larp-evidence); ev_gid=$(id -g larp-evidence); rt_uid=$(id -u larp-runtime); rt_gid=$(id -g larp-runtime)
  writer="import os, time
os.setgroups([]); os.setgid($ev_gid); os.setuid($ev_uid); os.umask(0o007)
from larp.contracts import Document
from larp.sources.store import SQLiteEvidenceStore
from larp.sources.store import FileArtifacts
store = SQLiteEvidenceStore('$state/evidence.sqlite', journal_mode='DELETE')
store.commit(Document.from_dict({'schema': 'EvidenceStateBatch.v1', 'batch_id': 'b1', 'issuer_id': 'ISSUER',
                                 'expected_state_version': 0, 'state': {'version': 1}, 'jobs': []}))
artifacts = FileArtifacts('$state/artifacts', group_readable=True)
open('$state/artifact.sha256', 'w').write(artifacts.put(b'synthetic public filing'))
open('$state/ready', 'w').close()
time.sleep(120)"
  (cd /opt/larp/current && exec $py -c "$writer") &
  writer_pid=$!
  for _ in $(seq 100); do [[ -e $state/ready ]] && break; sleep 0.1; done
  [[ -e $state/ready ]] || fail "evidence writer did not start"
  reader="import os, sqlite3, sys
os.setgroups([int(g) for g in sys.argv[1:]]); os.setgid($rt_gid); os.setuid($rt_uid); os.umask(0o077)
from larp.sources.store import SQLiteEvidenceStore
from larp.sources.store import FileArtifacts
store = SQLiteEvidenceStore('$state/evidence.sqlite', read_only=True)
assert store.read_state('ISSUER').read()['version'] == 1
saved = open('$state/artifact.sha256').read()
assert FileArtifacts('$state/artifacts').get(saved) == b'synthetic public filing'
try:
    store.db.execute('DELETE FROM estates')
except sqlite3.OperationalError:
    pass
else:
    raise SystemExit('read-only store wrote')"
  (cd /opt/larp/current && $py -c "$reader" "$ev_gid") || fail "runtime with the evidence group cannot read"
  ! (cd /opt/larp/current && $py -c "$reader" 2>/dev/null) || fail "runtime without the evidence group read the store"
  [[ -z $(find "$state" -perm /o=rwx) ]] || fail "evidence files accessible to others"
  kill "$writer_pid"; wait "$writer_pid" 2>/dev/null || true
  # R15: the reader opens first while the writer is closed, and remains open through writer restart/commit.
  first_reader="import os, time
os.setgroups([$ev_gid]); os.setgid($rt_gid); os.setuid($rt_uid); os.umask(0o077)
from pathlib import Path
from larp.sources.store import SQLiteEvidenceStore
store = SQLiteEvidenceStore('$state/evidence.sqlite', read_only=True)
assert store.read_state('ISSUER').read()['version'] == 1
assert not Path('$state/evidence.sqlite-wal').exists() and not Path('$state/evidence.sqlite-shm').exists()
Path('$state/reader-ready').touch()
deadline = time.monotonic() + 10
while store.read_state('ISSUER').read()['version'] != 2:
    assert time.monotonic() < deadline, 'writer restart/commit not visible'
    time.sleep(0.05)
store.close()"
  (cd /opt/larp/current && exec $py -c "$first_reader") &
  reader_pid=$!
  for _ in $(seq 100); do [[ -e $state/reader-ready ]] && break; sleep 0.1; done
  [[ -e $state/reader-ready ]] || fail "closed-writer reader did not start"
  restart_writer="import os
os.setgroups([]); os.setgid($ev_gid); os.setuid($ev_uid); os.umask(0o007)
from larp.contracts import Document
from larp.sources.store import SQLiteEvidenceStore
store = SQLiteEvidenceStore('$state/evidence.sqlite', journal_mode='DELETE')
assert store.read_state('ISSUER').read()['version'] == 1
store.commit(Document.from_dict({'schema': 'EvidenceStateBatch.v1', 'batch_id': 'b2', 'issuer_id': 'ISSUER',
                                 'expected_state_version': 1, 'state': {'version': 2}, 'jobs': []}))
store.close()"
  (cd /opt/larp/current && $py -c "$restart_writer") || fail "writer cannot restart with reader open"
  wait "$reader_pid" || fail "reader did not see restarted writer's commit"
  final_writer="import os
os.setgroups([]); os.setgid($ev_gid); os.setuid($ev_uid)
from larp.sources.store import SQLiteEvidenceStore
store = SQLiteEvidenceStore('$state/evidence.sqlite', journal_mode='DELETE')
assert store.read_state('ISSUER').read()['version'] == 2
store.close()"
  (cd /opt/larp/current && $py -c "$final_writer") || fail "writer cannot restart after reader closes"
  [[ ! -e $state/evidence.sqlite-wal && ! -e $state/evidence.sqlite-shm ]] || fail "shared reader made WAL sidecars"
  rm -rf "$state"
fi
# The other role is refused on this host.
other=$([[ $role == signer ]] && echo primary || echo signer)
! bash "$provision" "$other" /bundle.tar.gz --expect-sha256 "$sha" --no-systemctl >/dev/null 2>&1 \
  || fail "other role accepted"
# A tampered bundle is refused before anything is installed.
mkdir -p /tmp/tamper && tar -xzf /bundle.tar.gz -C /tmp/tamper
echo '# tampered' >> /tmp/tamper/larp-*/release/larp/__init__.py
tar -czf /tmp/tampered.tar.gz -C /tmp/tamper .
! bash "$provision" "$role" /tmp/tampered.tar.gz --expect-sha256 "$sha" --no-systemctl >/dev/null 2>&1 \
  || fail "tampered bundle accepted against the original hash"
# Even with its own hash passed, the bundle's SHA256SUMS still refuses the changed file.
! bash "$provision" "$role" /tmp/tampered.tar.gz --expect-sha256 "$(sha256sum /tmp/tampered.tar.gz | cut -d' ' -f1)" \
  --no-systemctl >/dev/null 2>&1 || fail "tampered bundle accepted"
echo "PASS[$role]: build $build, units: $units"
EOF

for role in primary signer; do
  docker run --rm --network none ${platform:+--platform "$platform"} \
    -v "$bundle:/bundle.tar.gz:ro" -v "$work/checks.sh:/checks.sh:ro" "$image" bash /checks.sh "$role"
done
