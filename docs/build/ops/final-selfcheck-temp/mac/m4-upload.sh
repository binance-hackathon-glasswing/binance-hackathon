#!/bin/bash
# M4U (Mac, Yao, AWS write): upload the M4 package to its own prefix; hashes are rechecked against package-record.json.
#   bash mac/m4-upload.sh <M3 stamp>
set -euo pipefail
MAIN=${LARP_REPO:-/Users/songyaozhu/binance-hackathon}
P=$MAIN/deploy/activation/selfcheck-temp-20261028/private/package-${1:?M3 stamp}
B=$(python3 -I -c "import json,sys;t=json.load(open(sys.argv[1]));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)" "$MAIN/deploy/activation/tf-output.json")
python3 -I - "$P" <<'PY' | while read -r n prefix; do
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1]); r = json.loads((p / 'package-record.json').read_text())
bad = [n for n, sha in r['hashes'].items() if hashlib.sha256((p / n).read_bytes()).hexdigest() != sha]
if bad:
    sys.exit('hash differs: ' + ','.join(bad))  # nothing uploaded
for n in r['hashes']:
    print(n, r['prefix'])
PY
  aws --profile larp --region ap-southeast-2 s3 cp --only-show-errors "$P/$n" "s3://$B/$prefix$n"
  echo "uploaded $n"
done
echo M4U_DONE
