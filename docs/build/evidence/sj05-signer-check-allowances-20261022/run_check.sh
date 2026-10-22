#!/bin/bash
# SJ-05 Part A: local signer check against the original RC3a bundle (IDEA-049-C SJ-05). No DB, key or host.
set -uo pipefail
S=/private/tmp/claude-501/-Users-songyaozhu-binance-hackathon/2078970b-af18-443d-91c3-0b71318bd568/scratchpad
R=$S/rc3a-dl/root/larp-fa1b6c966f18-x86_64/release
CI=$S/rc3a-dl/root/larp-fa1b6c966f18-x86_64/release-manifest.json
SIGNER=/private/tmp/claude-501/-Users-songyaozhu-binance-hackathon/b7ae8d2a-b6f5-46c8-9656-d52fff1a9753/scratchpad/host/signer-candidate-20261022T022846Z/signer.json
O=$S/sj05/out; rm -rf "$O"; mkdir -m 700 "$O"
P=$S/venv-rc3a/bin/python; export PYTHONDONTWRITEBYTECODE=1; unset PYTHONPATH
BUILD=fa1b6c966f186103c8dfaee5438e0d00e4edec9a
cd "$R"
echo "inputs signer=$(shasum -a 256 "$SIGNER"|cut -d' ' -f1) ci=$(shasum -a 256 "$CI"|cut -d' ' -f1)"
echo "== A2 unbound CI manifest"
$P -m larp.signer.service check --config "$SIGNER" --manifest "$CI" --root "$R"; echo "exit=$?"
cat > "$O/registration-evidence.local.json" <<J
{"schema":"RegistrationEvidence.v1","build_id":"$BUILD","repository":"https://github.com/binance-hackathon-glasswing/binance-hackathon","evidence_ref":"LOCAL CHECK ONLY (IDEA-049-C SJ-05): not the host's registration evidence; binds the original RC3a CI manifest to the candidate signer.json on Yao's Mac."}
J
echo "== A3 bind"
$P -m larp.runtime.preflight --bind "$CI" --root "$R" --output "$O/release.bound.json" \
  --registration-evidence "$O/registration-evidence.local.json" --service-config signer="$SIGNER"; echo "exit=$?"
$P -c "import json,sys;from larp.contracts import Document;d=Document(open(sys.argv[1],'rb').read()).read();print('ci_manifest_sha256',d['ci_manifest_sha256'],'build',d['build_id'],'files',len(d['files']),'service_configs',d['service_configs_sha256'])" "$O/release.bound.json"
echo "bound=$(shasum -a 256 "$O/release.bound.json"|cut -d' ' -f1)"
echo "== preflight verify (host profile env pins, signer config)"
$P -m larp.runtime.preflight --manifest "$O/release.bound.json" --root "$R" --profile host --service-config signer="$SIGNER"; echo "exit=$?"
echo "== A4 check"
$P -m larp.signer.service check --config "$SIGNER" --manifest "$O/release.bound.json" --root "$R"; echo "exit=$?"
echo "== A5 tamper (one trailing byte appended)"
install -m 600 "$SIGNER" "$O/signer.tampered.json"; printf ' ' >> "$O/signer.tampered.json"
$P -m larp.signer.service check --config "$O/signer.tampered.json" --manifest "$O/release.bound.json" --root "$R"; echo "exit=$?"
rm -f "$O/signer.tampered.json"
