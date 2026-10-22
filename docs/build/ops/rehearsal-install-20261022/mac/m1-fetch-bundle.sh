#!/bin/bash
# M1 (Mac, read-only): download the mirror-CI bundle for the merged canonical head, verify it, write build.env.
#   bash mac/m1-fetch-bundle.sh <mirror run id>
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RUN=$1
REPO=Cookiemunchrr/larp-ci-mirror
BUILD=$(git -C /Users/songyaozhu/binance-hackathon rev-parse origin/codex/system-testing-20261012)
[[ $(gh run view "$RUN" -R $REPO --json headSha -q .headSha) == "$BUILD" ]] || { echo "run is for another commit"; exit 3; }
[[ $(gh run view "$RUN" -R $REPO --json conclusion -q .conclusion) == success ]] || { echo "run did not succeed"; exit 3; }
B=$HERE/bundle; [[ ! -e $B ]] || { echo "bundle/ exists; not overwriting"; exit 3; }
gh run download "$RUN" -R $REPO -n larp-bundle-x86_64 -D "$B"
N=larp-${BUILD:0:12}-x86_64
GZ=$(shasum -a 256 "$B/$N.tar.gz" | cut -c1-64)
grep -q "$GZ" "$B/$N.tar.gz.sha256" || { echo "sidecar differs"; exit 3; }
mkdir "$B/x" && tar -xzf "$B/$N.tar.gz" -C "$B/x"
grep -q "^build_id=$BUILD$" "$B/x/$N/BUNDLE.env" || { echo "bundle is for another build"; exit 3; }
(cd "$B/x/$N" && shasum -a 256 -c --quiet SHA256SUMS) || { echo "bundle checksum mismatch"; exit 3; }
cmp -s "$B/$N.release.json" "$B/x/$N/release-manifest.json" || { echo "published manifest differs from the bundle's"; exit 3; }
cat > "$HERE/build.env" <<ENV
BUILD=$BUILD
BUNDLE=$N
BUNDLE_SHA256=$GZ
MANIFEST_SHA256=$(shasum -a 256 "$B/x/$N/release-manifest.json" | cut -c1-64)
PROVISION_SHA256=$(shasum -a 256 "$B/x/$N/provision.sh" | cut -c1-64)
CA_SHA256=$(grep '^rds_ca_sha256=' "$B/x/$N/BUNDLE.env" | cut -d= -f2)
MIRROR_RUN=$RUN
ENV
cat "$HERE/build.env"
echo M1_DONE
