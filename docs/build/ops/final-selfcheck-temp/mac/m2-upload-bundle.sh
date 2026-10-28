#!/bin/bash
# M2 (Mac, Yao, AWS write): upload Keith's verified release bundle temp-selfcheck-2aa95617 to the artifact bucket releases/.
set -euo pipefail
MAIN=${LARP_REPO:-/Users/songyaozhu/binance-hackathon}
O=$MAIN/deploy/activation/selfcheck-temp-20261028/bundle; N=larp-2aa95617bf92-x86_64
[[ $(shasum -a 256 "$O/$N.tar.gz" | cut -c1-64) == a4511e4aa314e92e3f2d5e5f9bf447b934523f78f70ff651c254bdf4a242cbf3 ]] || { echo "bundle hash differs"; exit 3; }
[[ $(shasum -a 256 "$O/$N.release.json" | cut -c1-64) == 213ab1b259377c0cb5b8c67835855267f73ed84fe1a7d5d6c14c253dd605d999 ]] || { echo "manifest differs"; exit 3; }
B=$(python3 -I -c "import json,sys;t=json.load(open(sys.argv[1]));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)" "$MAIN/deploy/activation/tf-output.json")
for f in $N.tar.gz $N.tar.gz.sha256 $N.release.json; do
  aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$O/$f" "s3://$B/releases/$f"
done
aws --profile larp --region ap-southeast-2 s3api head-object --bucket "$B" --key "releases/$N.tar.gz" \
  --query '{bytes:ContentLength,sse:ServerSideEncryption}' --output json
echo M2_DONE
