#!/bin/bash
# M2 (Mac, Yao, AWS write): upload Keith's verified release bundle temp-selfcheck-e261bcfc to the artifact bucket releases/.
set -euo pipefail
MAIN=${LARP_REPO:-/Users/songyaozhu/binance-hackathon}
O=$MAIN/deploy/activation/selfcheck-temp-20261028/bundle-e261; N=larp-e261bcfc7a33-x86_64
[[ $(shasum -a 256 "$O/$N.tar.gz" | cut -c1-64) == 1a58277c8919d49980388e04df7bc9fe119db0c8621fffcf7a64a1232b6ce5c1 ]] || { echo "bundle hash differs"; exit 3; }
[[ $(shasum -a 256 "$O/$N.release.json" | cut -c1-64) == 7635b1965a7655f22953d5d61702af1ac57c26ac1b386db575e3c48ac766d41c ]] || { echo "manifest differs"; exit 3; }
B=$(python3 -I -c "import json,sys;t=json.load(open(sys.argv[1]));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)" "$MAIN/deploy/activation/tf-output.json")
for f in $N.tar.gz $N.tar.gz.sha256 $N.release.json; do
  aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$O/$f" "s3://$B/releases/$f"
done
aws --profile larp --region ap-southeast-2 s3api head-object --bucket "$B" --key "releases/$N.tar.gz" \
  --query '{bytes:ContentLength,sse:ServerSideEncryption}' --output json
echo M2_DONE
