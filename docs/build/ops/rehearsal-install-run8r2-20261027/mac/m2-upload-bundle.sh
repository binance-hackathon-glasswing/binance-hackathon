#!/bin/bash
# M2 (Mac, Yao): upload the verified bundle, its .sha256 and .release.json to the artifact bucket releases/.
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/pins.sh"
O=$HERE/bundle
[[ $(shasum -a 256 "$O/$BUNDLE.tar.gz" | cut -c1-64) == "$BUNDLE_SHA256" ]]
B=$(python3 -I -c "import json,os;t=json.load(open(os.environ['LARP_REPO']+'/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
for f in $BUNDLE.tar.gz $BUNDLE.tar.gz.sha256 $BUNDLE.release.json; do
  aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$O/$f" "s3://$B/releases/$f"
done
aws --profile larp --region ap-southeast-2 s3api head-object --bucket "$B" --key "releases/$BUNDLE.tar.gz" \
  --query '{bytes:ContentLength,sse:ServerSideEncryption}' --output json
echo M2_DONE
