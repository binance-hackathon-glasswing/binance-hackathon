#!/bin/sh
# Manual push: if batch mode still fails to push by the next UTC midnight, some files stay under .ai-seeds/batch/;
# the SDK prints a warning and stops retrying automatically. Upload them one by one with this script. Files over the
# service limit (10 MB / 100,000 lines) are split on line boundaries before upload, so a whole-day <date>.jsonl that
# was never split can also be passed directly.
# Each request is signed with HMAC-SHA256 as described in section 2 of PROTOCOL.md; requires openssl and curl.
#
#   export AI_SEEDS_ADDRESS=0x<your wallet address>
#   export AI_SEEDS_SECRET=<secret issued at registration>
#   sh manual_push.sh .ai-seeds/batch/2026-09-25.part1.jsonl [more files ...]
#
# Files are uploaded to https://api.commonservice.io/ai-seeds-event-log.
# Pass at least one file (the sample is never uploaded by default, so demo data is not recorded under your wallet). Success returns {"lines":…,"events":…,"records":…,"status":"STORED"};
# re-uploading is harmless (deduplicated by event ID). If you get 401 TIMESTAMP_SKEW, fix your local clock first.
set -eu
AI_SEEDS_URL=${AI_SEEDS_URL:-https://api.commonservice.io/ai-seeds-event-log}
: "${AI_SEEDS_ADDRESS:?please set AI_SEEDS_ADDRESS}"
: "${AI_SEEDS_SECRET:?please set AI_SEEDS_SECRET}"
[ "$#" -gt 0 ] || { echo "usage: sh manual_push.sh <file.jsonl> [more files ...]" >&2; exit 2; }

address=$(printf '%s' "$AI_SEEDS_ADDRESS" | tr 'A-F' 'a-f')
MAX_BYTES=10000000   # below the service limit of 10485760 bytes
MAX_LINES=100000

push() {
  echo "== $1"
  ts="$(date +%s)000"
  nonce=$(openssl rand -hex 16)
  content=$(openssl dgst -sha256 -r "$1" | cut -d' ' -f1)
  signature=$(printf 'POST\n/v1/files\n%s\n%s\n%s\n%s' "$ts" "$nonce" "$address" "$content" \
    | openssl dgst -sha256 -hmac "$AI_SEEDS_SECRET" -r | cut -d' ' -f1)
  curl -sS -X POST "${AI_SEEDS_URL%/}/v1/files" \
    -H "X-AI-Seeds-Timestamp: $ts" \
    -H "X-AI-Seeds-Nonce: $nonce" \
    -H "X-AI-Seeds-Signature: $signature" \
    -F "address=${AI_SEEDS_ADDRESS}" \
    -F "file=@$1"
  echo
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
for f in "$@"; do
  bytes=$(wc -c < "$f" | tr -d ' ')
  lines=$(wc -l < "$f" | tr -d ' ')
  if [ "$bytes" -le "$MAX_BYTES" ] && [ "$lines" -le "$MAX_LINES" ]; then
    push "$f"
    continue
  fi
  # Too big for one request: split on line boundaries into parts within the limits.
  name=$(basename "$f")
  LC_ALL=C awk -v out_prefix="$tmp/$name.split" -v maxb="$MAX_BYTES" -v maxl="$MAX_LINES" '
    { n = length($0) + 1
      if (out == "" || size + n > maxb || count >= maxl) {
        if (out != "") close(out)
        part++; out = out_prefix part; size = 0; count = 0
      }
      print > out; size += n; count++ }' "$f"
  for p in "$tmp/$name.split"*; do
    push "$p"
  done
done
