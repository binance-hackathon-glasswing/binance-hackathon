#!/usr/bin/env bash
# IDEA-057 Q10: start the read-only quote capture and leave it running in the background.
#
# summarize needs samples on 3 UTC days including a weekend. Start before Sat Oct 17 00:00 UTC, or the next weekend
# (Oct 24-25) is after the rehearsal window opens (Oct 21). Quotes only: nothing is signed, approved or broadcast, and
# no wallet key or AI_SEEDS_SECRET is read. The Web3 key pair comes from the environment or ./.env and is never printed.
set -euo pipefail
dry=0
if [[ ${1:-} == --dry-run ]]; then dry=1; shift; fi
if [[ $# -ne 3 ]]; then
  echo "usage: $0 [--dry-run] <public wallet address> <until, UTC e.g. 2026-10-19T00:00:00Z> <capture dir>" >&2
  echo "Start it before the weekend: summarize refuses captures without a weekend (UTC) sample." >&2
  exit 2
fi
address=$1 until=$2
mkdir -p "$3" && dir=$(cd "$3" && pwd)  # absolute: the capture runs from the repo root
if [[ -z ${BINANCE_API_KEY:-} || -z ${BINANCE_SECRET_KEY:-} ]] && [[ -f .env ]]; then
  # Read only the two names from .env; never source it and never echo values.
  while IFS='=' read -r name value; do
    case $name in BINANCE_API_KEY|BINANCE_SECRET_KEY) export "$name=${value%$'\r'}";; esac
  done < <(grep -E '^(BINANCE_API_KEY|BINANCE_SECRET_KEY)=' .env)
fi
if [[ -z ${BINANCE_API_KEY:-} || -z ${BINANCE_SECRET_KEY:-} ]]; then
  echo "BINANCE_API_KEY / BINANCE_SECRET_KEY are not set (environment or ./.env); nothing started" >&2
  exit 2
fi
root=$(cd "$(dirname "$0")/.." && pwd)
python=${PYTHON:-python3}
cmd=("$python" -m larp.marketdata.cost_summary capture --address "$address" --out-dir "$dir" --until "$until"
     --interval-seconds "${INTERVAL_SECONDS:-600}")
if command -v caffeinate >/dev/null 2>&1; then cmd=(caffeinate -i "${cmd[@]}"); fi  # keep a Mac awake
log="$dir/capture.log"
if [[ $dry == 1 ]]; then
  printf 'would run (in %s, log %s):' "$root" "$log"; printf ' %q' "${cmd[@]}"; echo
  exit 0
fi
cd "$root"
nohup "${cmd[@]}" >>"$log" 2>&1 &
pid=$!
# A rejected key, region or argument stops the capture within seconds; say so now, not after the weekend.
sleep "${STARTUP_CHECK_SECONDS:-10}"
if ! kill -0 "$pid" 2>/dev/null; then
  echo "capture exited during startup; last log lines:" >&2
  tail -n 5 "$log" >&2
  exit 1
fi
echo "capture running as PID $pid until $until; log: $log"
echo "summarize afterwards: $python -m larp.marketdata.cost_summary summarize --captures $dir --output <summary.json>"
