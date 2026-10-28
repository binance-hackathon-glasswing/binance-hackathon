#!/bin/bash
# M3 (Mac; IDEA-110 TEMP-SC run sheet step 4): capture -> prepare -> FINAL caps inputs -> prepare with caps, back to
# back, because the capture and the quotes are each valid for 300 s. Read-only: Web3 reads/quotes and public chain
# reads; no AWS, host, database, key, signing or upload. Prints status and hashes only.
#
#   FINAL_WALLET=0x... ./m3-capture-prepare-caps.sh
#
# Run from a clean checkout of the pushed tool commit (this file's checkout). BUILD stays the release bundle 2aa95617:
# final_caps_inputs.py runs on the Mac only and is not part of the installed bundle.
set -euo pipefail
umask 077
REL="$(cd "$(dirname "$0")/../../../../.." && pwd)"
MAIN=${LARP_REPO:-/Users/songyaozhu/binance-hackathon}
PY=${LARP_PY:-$HOME/larp-monitor-venv/bin/python}
W=${FINAL_WALLET:?set FINAL_WALLET}
BUILD=2aa95617bf9217455d88446f44c7cdbd8276f88b
CA_SHA256=d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b
TF=$MAIN/deploy/activation/tf-output.json
RPC=$MAIN/deploy/activation/balance-rpc/selected-providers.json
HISTORY=$REL/docs/build/evidence/th01-live-20261026/token-history.json
ADOPTION=${MODEL_ADOPTION_REF:-"IDEA-110 TEMP-SC on FS1 routing 9b86c732 (approved Yao Zhu + Isaac, 2026-10-28 SGT)"}
[[ -z $(git -C "$REL" status --porcelain --untracked-files=no) ]] || { echo "tool checkout is dirty"; exit 3; }
git -C "$REL" branch -r --contains HEAD | grep -q . || { echo "tool commit is not pushed"; exit 3; }
[[ $(git -C "$REL" diff --name-only $BUILD HEAD -- larp migrations config deploy) == "" ]] || { echo "runtime sources differ from $BUILD"; exit 3; }
[[ $(shasum -a 256 "$HISTORY" | cut -c1-64) == 5e572570bc24fb2ca7b692dccf71f67a37c5fac3d75330e4558634cf45417be9 ]] || { echo "token history differs"; exit 3; }
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
P=$MAIN/deploy/activation/selfcheck-temp-20261028/private; install -d -m 0700 "$P"
PREP=$REL/deploy/activation/selfcheck-temp-$STAMP   # prepare_fs1 writes only into the git-ignored deploy/activation
cd "$REL"
"$PY" -m tools.deploy.prepare_shadow capture --env-file "$MAIN/.env" --wallet "$W" \
  --artifact-root "$P/capture-artifacts-$STAMP" --output "$P/capture-$STAMP.json" --balance-rpc-config "$RPC"
common=(--temp-self-check --terraform-output "$TF" --wallet "$W" --capture "$P/capture-$STAMP.json"
  --token-history-config "$HISTORY" --balance-rpc-config "$RPC" --rds-ca-sha256 "$CA_SHA256" --build-id "$BUILD"
  --model-adoption-ref "$ADOPTION")
"$PY" -m tools.deploy.prepare_fs1 "${common[@]}" --out "$PREP/prepared" | tee "$P/prepare-$STAMP.json"
"$PY" -m tools.deploy.final_caps_inputs --prepared "$PREP/prepared" --terraform-output "$TF" \
  --rds-ca-sha256 "$CA_SHA256" --balance-rpc-config "$RPC" --env-file "$MAIN/.env" --output "$P/caps-$STAMP" \
  | tee "$P/caps-$STAMP.json"
"$PY" -m tools.deploy.prepare_fs1 "${common[@]}" --out "$PREP/prepared-with-caps" \
  --caps-inputs "$P/caps-$STAMP/inputs.json" --services-out "$P/services-$STAMP" | tee "$P/prepare-caps-$STAMP.json"
cmp -s "$PREP/prepared/strategy-profile.json" "$PREP/prepared-with-caps/strategy-profile.json" || { echo "profile bytes differ"; exit 3; }
echo "M3 stamp $STAMP"
echo "profile_sha256 $(shasum -a 256 "$PREP/prepared-with-caps/strategy-profile.json" | cut -c1-64)"
echo "signer_sha256  $(shasum -a 256 "$P/services-$STAMP/signer.json" | cut -c1-64)"
echo "execution_sha256 $(shasum -a 256 "$P/services-$STAMP/execution.json" | cut -c1-64)"
