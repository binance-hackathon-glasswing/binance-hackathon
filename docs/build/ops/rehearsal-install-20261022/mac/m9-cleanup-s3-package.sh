#!/bin/bash
# M9 (Mac, Yao): after P3 and S1 both passed, delete the S3 transfer copies of the host package. execution.json
# carries the execution RPC URL and runtime.json the balance RPC providers. The bundle under releases/ stays.
#   bash mac/m9-cleanup-s3-package.sh <prefix printed by M4>
set -euo pipefail
PREFIX=$1
[[ $PREFIX =~ ^releases/rehearsal-[0-9t]+z/$ ]] || { echo "unexpected prefix"; exit 3; }
B=$(/opt/homebrew/bin/python3.12 -I -c "import json;t=json.load(open('/Users/songyaozhu/binance-hackathon/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
/opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3 rm --only-show-errors --recursive "s3://$B/$PREFIX"
/opt/homebrew/bin/aws --profile larp --region ap-southeast-2 s3 ls "s3://$B/$PREFIX" || true
echo M9_DONE
