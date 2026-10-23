#!/bin/bash
# M2 (Mac, Yao): upload the verified bundle, its .sha256 and .release.json to the artifact bucket releases/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; source "$HERE/build.env"
O=$HERE/bundle
[[ $(shasum -a 256 "$O/$BUNDLE.tar.gz" | cut -c1-64) == "$BUNDLE_SHA256" ]]
B=$(/opt/homebrew/bin/python3.12 -I -c "import json;t=json.load(open('/Users/songyaozhu/binance-hackathon/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
for f in $BUNDLE.tar.gz $BUNDLE.tar.gz.sha256 $BUNDLE.release.json; do
  /opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$O/$f" "s3://$B/releases/$f"
done
/opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3api head-object --bucket "$B" --key "releases/$BUNDLE.tar.gz" \
  --query '{bytes:ContentLength,sse:ServerSideEncryption}' --output json
echo M2_DONE
