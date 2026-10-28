# P2 (primary or signer, host mutation): install the mirror-CI bundle with its own verified provision.sh.
#   p2-provision.sh <primary|signer> <bucket> <bundle name> <bundle sha256> <provision.sh sha256>
# Starts nothing. On primary, larp-execution stays disabled until P5.
set -euo pipefail
umask 077
ROLE=$1; BUCKET=$2; N=$3; GZ=$4; PROV=$5
case $ROLE in primary) OTHER=signer ;; signer) OTHER=primary ;; *) echo "role must be primary or signer"; exit 3 ;; esac
[[ ! -e /etc/larp/role-$OTHER ]] || { echo "this host is provisioned as $OTHER"; exit 3; }
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-signer larp-archive.timer; do
  [[ $(systemctl is-active $u 2>/dev/null || true) != active ]] || { echo "$u is active; refusing"; exit 3; }
done
[[ ! -e /etc/larp/release.json ]] || { echo "release.json in place; run p1 first"; exit 3; }
install -d -m 0700 /root/releases
aws s3 cp --only-show-errors "s3://$BUCKET/releases/$N.tar.gz" /root/releases/$N.tar.gz
aws s3 cp --only-show-errors "s3://$BUCKET/releases/$N.tar.gz.sha256" /root/releases/$N.tar.gz.sha256
[[ $(sha256sum /root/releases/$N.tar.gz | cut -d' ' -f1) == "$GZ" ]] || { echo "bundle hash differs"; exit 3; }
grep -q "$GZ" /root/releases/$N.tar.gz.sha256 || { echo "sidecar differs"; exit 3; }
W=$(mktemp -d /root/prov.XXXXXX); trap 'rm -rf "$W"' EXIT
tar -xzf /root/releases/$N.tar.gz -C "$W" --no-same-owner $N/provision.sh
[[ $(sha256sum "$W/$N/provision.sh" | cut -d' ' -f1) == "$PROV" ]] || { echo "provision.sh differs"; exit 3; }
bash "$W/$N/provision.sh" "$ROLE" /root/releases/$N.tar.gz --expect-sha256 "$GZ"
if [[ $ROLE == primary ]]; then systemctl disable larp-execution.service; fi
if [[ $ROLE == signer ]]; then systemctl disable larp-signer.service; fi
readlink -f /opt/larp/current
echo "manifest sha256 $(sha256sum /opt/larp/current/release-manifest.json | cut -d' ' -f1)"
echo "rds-ca $(sha256sum /etc/larp/rds-ca.pem | cut -d' ' -f1)"
echo P2_DONE
