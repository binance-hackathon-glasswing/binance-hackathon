#!/bin/bash
# Owner-run after step 7: remove the transfer copies of the prepared host files (runtime.json carries private RPC
# URLs) from the artifact bucket, as in PC-AWS07. The installed /etc/larp files and the local package are kept.
# Leaves the release bundle objects in place.  $1 = s3 prefix printed by 05-prepare.py
set -euo pipefail
P=${1:?prefix}
[[ $P == releases/llm-trial-*/ ]] || { echo "unexpected prefix"; exit 3; }
B=$(/opt/homebrew/bin/python3.12 -I -c "import json;t=json.load(open('/Users/songyaozhu/binance-hackathon/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
for n in runtime.json uploader.json operations.json strategy-profile.json session-calendar.json initial-state.json \
         evidence.env model-routing.json; do
  /opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3 rm --only-show-errors "s3://$B/$P$n"
done
echo CLEANUP_DONE
