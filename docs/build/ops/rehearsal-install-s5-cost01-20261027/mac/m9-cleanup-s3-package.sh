#!/bin/bash
# M9 (Mac, Yao): after P3 and S1 both passed, delete the S3 transfer copies of the host package. execution.json
# carries the execution RPC URL and runtime.json the balance RPC providers. The bundle under releases/ stays.
#   bash mac/m9-cleanup-s3-package.sh <prefix printed by M4>
set -euo pipefail
umask 077
[[ ${1:-} == releases/s5-cost01-*/* && ${1:-} != *..* ]] || { echo "expected the exact s5-cost01 transfer prefix"; exit 3; }
PREFIX=$1
[[ $PREFIX =~ ^releases/s5-cost01-[0-9t]+z/$ ]] || { echo "unexpected prefix"; exit 3; }
B=$(python3 -I -c "import json,os;t=json.load(open(os.environ['LARP_REPO']+'/deploy/activation/tf-output.json'));v=t['artifact_bucket'];print(v['value'] if isinstance(v,dict) else v)")
AWS=(aws --profile larp --region ap-southeast-2)
# SJ-06-RV01: the artifacts bucket is versioned, so `s3 rm` alone only adds delete markers and the old versions
# (RPC URLs, DB host) stay readable. Delete every object version and delete marker under the prefix.
"${AWS[@]}" s3api list-object-versions --bucket "$B" --prefix "$PREFIX" --output json > /tmp/m9-$$.json
python3 -I - /tmp/m9-$$.json "$PREFIX" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
if d.get('IsTruncated'):
    raise SystemExit('version listing truncated; stop')
objs = [dict(Key=o['Key'], VersionId=o['VersionId']) for k in ('Versions', 'DeleteMarkers') for o in (d.get(k) or [])]
if not all(o['Key'].startswith(sys.argv[2]) for o in objs):
    raise SystemExit('listing escaped the prefix; stop')
json.dump({'Objects': objs, 'Quiet': True}, open(sys.argv[1], 'w'))
print('versions to delete:', len(objs))
PY
if python3 -I -c "import json,sys;sys.exit(0 if json.load(open('/tmp/m9-$$.json'))['Objects'] else 1)"; then
  "${AWS[@]}" s3api delete-objects --bucket "$B" --delete "file:///tmp/m9-$$.json" --output json --query 'Errors'
fi
rm -f /tmp/m9-$$.json
left=$("${AWS[@]}" s3api list-object-versions --bucket "$B" --prefix "$PREFIX" --output json \
  | python3 -I -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('Versions') or [])+len(d.get('DeleteMarkers') or []))")
[[ $left == 0 ]] || { echo "versions remain under $PREFIX ($left); stop (no M9_DONE)"; exit 3; }
echo M9_DONE
