#!/bin/bash
# R4 (Mac, owner): upload the locally built ea25b52 bundle (PC-BUILD01: local build from merged PR178, NOT CI;
# every file except providers.py/manifest/BUNDLE.env is byte-identical to Keegan's CI 86b1476 bundle).
set -euo pipefail
O=/Users/songyaozhu/binance-hackathon/deploy/activation/redeploy-20261018/bundle
N=larp-ea25b5232565-x86_64
GZ=9c7ac630b777d8af3afabdc300d730bac1103bf5996d19dedc674bff1c0dc3ca
[[ $(shasum -a 256 $O/$N.tar.gz | cut -c1-64) == "$GZ" ]]
grep -q "$GZ" $O/$N.tar.gz.sha256
B=$(/opt/homebrew/bin/python3.12 -I -c "import json;t=json.load(open('/Users/songyaozhu/binance-hackathon/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
for f in $N.tar.gz $N.tar.gz.sha256 $N.release.json; do
  /opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$O/$f" "s3://$B/releases/$f"
done
/opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3api head-object --bucket "$B" --key "releases/$N.tar.gz" \
  --query '{bytes:ContentLength,sse:ServerSideEncryption}' --output json
echo R4_DONE
