#!/bin/bash
# Soak (Mac, read-only; IDEA-085 host check): IAM logins and login failures per hour from the RDS PostgreSQL log.
#   bash mac/soak-db-logins.sh [hours, default 3]
# Each RDS IAM login writes one "POST /authenticateRequest" trace line. Baseline with RC4 (one login per transaction):
# about 45,000 an hour (SJ-06 J8 incident). PASS for RC5: under 500 an hour, and no "canceling authentication due to
# timeout" or "PAM authentication failed" line. Prints counts only; the log stays in results/ (git-ignored).
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "$0")/.." && pwd)"; HOURS=${1:-3}
AWS=(aws --profile larp --region ap-southeast-2)
OUT=$HERE/results/soak-$(date -u +%Y%m%dT%H%M%SZ); install -d -m 0700 "$OUT"
bad=0
for f in $("${AWS[@]}" rds describe-db-log-files --db-instance-identifier larp-dev \
             --query "DescribeDBLogFiles[-$HOURS:].LogFileName" --output text); do
  "${AWS[@]}" rds download-db-log-file-portion --db-instance-identifier larp-dev --log-file-name "$f" \
    --starting-token 0 --output text > "$OUT/$(basename "$f")"
  logins=$(grep -c 'POST /authenticateRequest' "$OUT/$(basename "$f")" || true)
  fails=$(grep -cE 'canceling authentication due to timeout|PAM authentication failed' "$OUT/$(basename "$f")" || true)
  echo "$f logins=$logins auth_failures=$fails"
  [[ $logins -lt 500 && $fails -eq 0 ]] || bad=1
done
echo "(the newest file is the current, partial hour)"
[[ $bad == 0 ]] || { echo "SOAK_CHECK: a file is over 500 logins or has an auth failure"; exit 1; }
echo SOAK_PASS
