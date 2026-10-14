#!/usr/bin/env bash
# Install a LARP release bundle on a host (IDEA-047 H02). Run as root; safe to run again with the same bundle.
#
#   provision.sh <primary|signer> <larp-BUILD-ARCH.tar.gz> [--no-systemctl]
#
# Works offline: the bundle (tools/build_release_bundle.py) carries CPython 3.12.15, every wheel and the RDS CA
# bundle, so the signer host, which has no internet route (IDEA-046 B2), installs it from the artifact bucket via the
# S3 gateway endpoint. It verifies every checksum, then installs:
#   /opt/larp/python/<version>+<tag>   CPython, root-owned
#   /opt/larp/releases/<build>         the release and its .venv, root-owned and read-only to services
#   /opt/larp/current                  symlink to the installed release
#   /etc/larp/                         root 0755; role marker; rds-ca.pem; /etc/larp/signer 0700 on the signer
#   one system user per service and only this role's systemd units (enabled, not started)
# It never writes a configuration, a release manifest, a secret or the wallet key, and never starts a service.
# Those are separate, reviewed steps (docs/build/architecture-deployment.md).
set -euo pipefail
umask 022

die() { echo "provision: $*" >&2; exit 1; }

[[ $# -ge 2 && $# -le 3 ]] || die "usage: provision.sh <primary|signer> <bundle.tar.gz> [--no-systemctl]"
role=$1
bundle=$2
systemctl_enabled=1
[[ ${3:-} == "" || ${3:-} == "--no-systemctl" ]] || die "unknown option ${3}"
[[ ${3:-} == "--no-systemctl" ]] && systemctl_enabled=0
[[ $(id -u) -eq 0 ]] || die "run as root"
case $role in
  primary) other=signer; users=(larp-runtime larp-execution larp-uploader larp-evidence larp-archive)
           units=(larp-runtime.service larp-execution.service larp-uploader.service larp-evidence.service
                  larp-archive.service larp-archive.timer) ;;
  signer)  other=primary; users=(larp-signer); units=(larp-signer.service) ;;
  *) die "role must be primary or signer" ;;
esac
for tool in tar gzip sha256sum useradd groupadd install; do
  command -v "$tool" >/dev/null || die "missing required tool: $tool"
done
[[ -f $bundle ]] || die "bundle not found"
[[ ! -e /etc/larp/role-$other ]] || die "this host is already provisioned as $other"

work=$(mktemp -d /tmp/larp-provision.XXXXXX)
trap 'rm -rf "$work"' EXIT
# Refuse absolute paths, parent references and links before extracting anything.
if tar -tvzf "$bundle" | awk '{print substr($1,1,1)}' | grep -qv '^[d-]$'; then die "bundle holds links or devices"; fi
if tar -tzf "$bundle" | grep -Eq '^/|(^|/)\.\.(/|$)'; then die "bundle paths escape"; fi
tar -xzf "$bundle" -C "$work" --no-same-owner --no-same-permissions
dirs=("$work"/larp-*)
[[ ${#dirs[@]} -eq 1 && -d ${dirs[0]} ]] || die "bundle must hold exactly one larp-* directory"
src=${dirs[0]}

# Every file except SHA256SUMS is listed, and every listed file matches.
(cd "$src" && sha256sum --check --strict --quiet SHA256SUMS) || die "bundle checksum mismatch"
listed=$(wc -l < "$src/SHA256SUMS")
present=$(cd "$src" && find . -type f ! -name SHA256SUMS | wc -l)
[[ $listed -eq $present ]] || die "bundle holds files outside SHA256SUMS"

declare -A meta
while IFS='=' read -r key value; do
  [[ $key =~ ^[a-z0-9_]+$ ]] || die "malformed BUNDLE.env"
  meta[$key]=$value
done < "$src/BUNDLE.env"
for key in build_id arch python_version python_tag python_file python_sha256 rds_ca_sha256; do
  [[ -n ${meta[$key]:-} ]] || die "BUNDLE.env lacks $key"
done
build=${meta[build_id]}
[[ $build =~ ^[0-9a-f]{40}$ ]] || die "invalid build id"
[[ $(uname -m) == "${meta[arch]}" ]] || die "bundle is for ${meta[arch]}, host is $(uname -m)"
[[ $(sha256sum "$src/python/${meta[python_file]}" | cut -d' ' -f1) == "${meta[python_sha256]}" ]] \
  || die "python archive differs from its pin"
pinned=$(grep "^${meta[arch]}=" "$src/release/deploy/host/python.lock" | cut -d= -f2)
[[ $pinned == "${meta[python_sha256]}" ]] || die "python pin differs from the release's deploy/host/python.lock"

install -d -m 0755 -o root -g root /opt/larp /opt/larp/python /opt/larp/releases /etc/larp

# CPython, once per pinned build.
python_dir=/opt/larp/python/${meta[python_version]}+${meta[python_tag]}
if [[ ! -x $python_dir/bin/python3 ]]; then
  rm -rf "$python_dir.partial"
  install -d -m 0755 "$python_dir.partial"
  tar -xzf "$src/python/${meta[python_file]}" -C "$python_dir.partial" --no-same-owner
  [[ -x $python_dir.partial/python/bin/python3 ]] || die "unexpected python archive layout"
  mv "$python_dir.partial/python" "$python_dir"
  rmdir "$python_dir.partial"
  chown -R root:root "$python_dir"
  chmod -R go-w "$python_dir"
fi
[[ $("$python_dir/bin/python3" -c 'import platform; print(platform.python_version())') == "${meta[python_version]}" ]] \
  || die "installed python version differs"

# The release and its venv: immutable once complete. A partial install from an interrupted run is redone.
release=/opt/larp/releases/$build
if [[ -f $release/.installed ]]; then
  cmp -s "$release/.installed" "$src/SHA256SUMS" || die "release $build is already installed from different bytes"
else
  rm -rf "$release"
  install -d -m 0755 "$release"
  cp -R "$src/release/." "$release/"
  "$python_dir/bin/python3" -m venv "$release/.venv"
  "$release/.venv/bin/python" -m pip install --quiet --no-index --no-deps --disable-pip-version-check \
    --find-links "$src/wheels" -r "$release/deploy/requirements-signer.lock" -r "$release/deploy/requirements-aws.lock"
  "$release/.venv/bin/python" -m pip check >/dev/null || die "installed packages are inconsistent"
  chown -R root:root "$release"
  chmod -R u=rwX,go=rX "$release"
  install -m 0444 "$src/SHA256SUMS" "$release/.installed"
fi
ln -sfn "$release" /opt/larp/current.new
mv -T /opt/larp/current.new /opt/larp/current

# One system user per service; no login, no home.
nologin=$(command -v nologin || echo /sbin/nologin)
for user in "${users[@]}"; do
  if ! id -u "$user" >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --home-dir /nonexistent --shell "$nologin" "$user"
  fi
done

install -m 0644 -o root -g root "$src/rds-ca.pem" /etc/larp/rds-ca.pem
[[ $(sha256sum /etc/larp/rds-ca.pem | cut -d' ' -f1) == "${meta[rds_ca_sha256]}" ]] || die "RDS CA bundle differs"
install -m 0444 -o root -g root /dev/null "/etc/larp/role-$role"
if [[ $role == signer ]]; then
  install -d -m 0700 -o root -g root /etc/larp/signer
fi

# Only this role's units. Units of the other role are never installed here.
install -d -m 0755 /etc/systemd/system
for unit in "${units[@]}"; do
  install -m 0644 -o root -g root "$release/deploy/systemd/$unit" "/etc/systemd/system/$unit"
done
if [[ $systemctl_enabled -eq 1 ]]; then
  systemctl daemon-reload
  for unit in "${units[@]}"; do
    [[ $unit == larp-archive.service ]] && continue  # started by its timer
    systemctl enable "$unit" >/dev/null
  done
fi

echo "provision: installed build $build for $role (python ${meta[python_version]}, units: ${units[*]})"
echo "provision: next, as root: write /etc/larp/<service>.json and /etc/larp/release.json$(
  [[ $role == signer ]] && echo ', and the wallet key as /etc/larp/signer/wallet.key (root, 0600)'); nothing was started"
