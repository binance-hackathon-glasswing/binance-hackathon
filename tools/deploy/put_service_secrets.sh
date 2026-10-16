#!/usr/bin/env bash
# Store the runtime and uploader service secrets in AWS Secrets Manager (IDEA-051; runbook.md §1.3).
#
# Run it yourself, in your own terminal. Never paste a secret into a chat, a commit or a shared document.
#   bash tools/deploy/put_service_secrets.sh --name larp-dev [--region ap-southeast-2] [--only runtime|uploader]
# AWS credentials come from your environment (for example AWS_PROFILE=larp after `aws login --profile larp`).
#
# What it writes, and nothing else:
#   <name>/runtime   {AI_SEEDS_ADDRESS, BINANCE_API_KEY, BINANCE_SECRET_KEY}  (larp/runtime/live.py RUNTIME_SECRETS)
#                    + optional LARP_AIAND_API_KEY, LARP_MODEL_API_KEY       (larp/runtime/credentials.py
#                      OPTIONAL_MODEL_SECRETS; only the shadow `aiand_routed` assessor reads them, IDEA-057)
#   <name>/uploader  {AI_SEEDS_ADDRESS, AI_SEEDS_SECRET}                      (larp/audit/service.py ALLOWED_SECRETS)
# The wallet key is NOT a Secrets Manager entry: it is the root-only file /etc/larp/signer/wallet.key on the signer.
#
# Values are read with hidden prompts and reach `aws` only on stdin: never on a command line, in a file or in the
# output. Only key names, secret IDs and the new version ID are printed. Each run replaces the whole secret value, so
# re-enter every key you want to keep. Press Enter at an optional prompt to leave that key out.
set -euo pipefail

name='' region='ap-southeast-2' only=''
while (($#)); do
  case "$1" in
    --name) name=${2:?}; shift 2 ;;
    --region) region=${2:?}; shift 2 ;;
    --only) only=${2:?}; shift 2 ;;
    *) echo "usage: $0 --name <terraform name, e.g. larp-dev> [--region R] [--only runtime|uploader]" >&2; exit 2 ;;
  esac
done
[[ $name =~ ^[a-z][a-z0-9-]{2,24}$ ]] || { echo "refused: --name must be the Terraform name (e.g. larp-dev)" >&2; exit 2; }
[[ -z $only || $only == runtime || $only == uploader ]] || { echo "refused: --only runtime|uploader" >&2; exit 2; }
command -v aws >/dev/null && command -v python3 >/dev/null || { echo "refused: needs aws and python3" >&2; exit 2; }

hidden() {  # hidden prompt; the value never appears on screen
  local value
  IFS= read -r -s -p "$1: " value; echo >&2
  [[ -n $value ]] || { echo "refused: $1 is empty" >&2; exit 2; }
  printf '%s' "$value"
}

optional() {  # hidden prompt; an empty answer leaves the key out
  local value
  IFS= read -r -s -p "$1 (optional; Enter to omit): " value; echo >&2
  printf '%s' "$value"
}

IFS= read -r -p "Wallet address (public, 0x…; the same address registered with ai-seeds): " address
[[ $address =~ ^0x[0-9a-fA-F]{40}$ ]] || { echo "refused: not an 0x address of 40 hex characters" >&2; exit 2; }

store() {  # store <secret-id> <name>… ; values come from the caller's variables, JSON is built on stdin
  local id=$1; shift
  echo "Writing $id with keys: $*" >&2
  local answer; IFS= read -r -p "Proceed? [y/N] " answer
  [[ $answer == y || $answer == Y ]] || { echo "skipped $id" >&2; return 0; }
  local key
  for key in "$@"; do printf '%s\n' "${!key}"; done \
    | python3 -c 'import json, sys
names = sys.argv[1:]
values = sys.stdin.read().split("\n")[:len(names)]
assert len(values) == len(names) and all(values)
sys.stdout.write(json.dumps(dict(zip(names, values))))' "$@" \
    | aws secretsmanager put-secret-value --region "$region" --secret-id "$id" \
        --secret-string file:///dev/stdin --query VersionId --output text \
    | sed "s|^|$id stored, version |" >&2
}

if [[ -z $only || $only == runtime ]]; then
  AI_SEEDS_ADDRESS=$address
  BINANCE_API_KEY=$(hidden 'BINANCE_API_KEY (Web3 Open API key)')
  BINANCE_SECRET_KEY=$(hidden 'BINANCE_SECRET_KEY')
  keys=(AI_SEEDS_ADDRESS BINANCE_API_KEY BINANCE_SECRET_KEY)
  # Model keys for the shadow-only AIand routing (IDEA-057). The routed assessor refuses to start without the AIand
  # key; without the OpenAI key every model call stays on AIand.
  LARP_AIAND_API_KEY=$(optional 'LARP_AIAND_API_KEY (AIand; needed for "assessor": "aiand_routed")')
  [[ -z $LARP_AIAND_API_KEY ]] || keys+=(LARP_AIAND_API_KEY)
  LARP_MODEL_API_KEY=$(optional 'LARP_MODEL_API_KEY (OpenAI)')
  [[ -z $LARP_MODEL_API_KEY ]] || keys+=(LARP_MODEL_API_KEY)
  store "$name/runtime" "${keys[@]}"
  unset BINANCE_API_KEY BINANCE_SECRET_KEY LARP_AIAND_API_KEY LARP_MODEL_API_KEY
fi
if [[ -z $only || $only == uploader ]]; then
  AI_SEEDS_ADDRESS=$address
  AI_SEEDS_SECRET=$(hidden 'AI_SEEDS_SECRET (64 hex characters)')
  [[ $AI_SEEDS_SECRET =~ ^[0-9a-fA-F]{64}$ ]] || { echo "refused: AI_SEEDS_SECRET must be 64 hex characters" >&2; exit 2; }
  store "$name/uploader" AI_SEEDS_ADDRESS AI_SEEDS_SECRET
  unset AI_SEEDS_SECRET
fi
