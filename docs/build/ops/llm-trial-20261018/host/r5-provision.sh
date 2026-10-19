# R5 (host mutation): install the ea25b52 bundle with its own verified provision.sh. $1 = artifact bucket.
# Keeps bb46234 and 86b1476 installed. Starts nothing; re-disables execution.
set -euo pipefail
BUCKET=$1
N=larp-ea25b5232565-x86_64
GZ=9c7ac630b777d8af3afabdc300d730bac1103bf5996d19dedc674bff1c0dc3ca
PROV=d7905de425118df3
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-archive.service larp-archive.timer; do
  [[ $(systemctl is-active $u || true) != active ]] || { echo "$u is active; run r3 first"; exit 3; }
done
[[ ! -e /etc/larp/release.json ]] || { echo "release.json still in place; run r3 first"; exit 3; }
install -d -m 0700 /root/releases
aws s3 cp --only-show-errors "s3://$BUCKET/releases/$N.tar.gz" /root/releases/$N.tar.gz
aws s3 cp --only-show-errors "s3://$BUCKET/releases/$N.tar.gz.sha256" /root/releases/$N.tar.gz.sha256
[[ $(sha256sum /root/releases/$N.tar.gz | cut -d' ' -f1) == "$GZ" ]] || { echo "bundle hash differs"; exit 3; }
grep -q "$GZ" /root/releases/$N.tar.gz.sha256 || { echo "sidecar differs"; exit 3; }
W=$(mktemp -d /root/prov.XXXXXX)
tar -xzf /root/releases/$N.tar.gz -C "$W" --no-same-owner $N/provision.sh
[[ $(sha256sum "$W/$N/provision.sh" | cut -c1-16) == "$PROV" ]] || { echo "provision.sh differs"; exit 3; }
bash "$W/$N/provision.sh" primary /root/releases/$N.tar.gz --expect-sha256 "$GZ"
rm -rf "$W"
systemctl disable larp-execution.service
readlink -f /opt/larp/current
ls -la /opt/larp/releases | sed -E 's/ +/ /g'
for u in larp-runtime larp-uploader larp-evidence larp-execution larp-archive.timer; do
  echo "$u enabled=$(systemctl is-enabled $u || true) active=$(systemctl is-active $u || true)"
done
echo "manifest sha256 $(sha256sum /opt/larp/current/release-manifest.json | cut -d' ' -f1)"
echo "rds-ca $(sha256sum /etc/larp/rds-ca.pem | cut -d' ' -f1)"
echo R5_DONE
