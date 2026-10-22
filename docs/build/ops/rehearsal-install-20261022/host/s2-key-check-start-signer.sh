# S2 (signer, host mutation, after Isaac's K1 key placement and P4 on primary): confirm the key file passes the
# loader and derives the configured wallet, then start larp-signer. Prints booleans and fixed texts only, never key
# material. Systemd hands the service its own copy through LoadCredential.
set -euo pipefail
K=/etc/larp/signer/wallet.key
[[ -f $K ]] || { echo "no key file; Isaac places it first (K1)"; exit 3; }
stat -c '%a %U:%G %h %n' /etc/larp/signer "$K"
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import json
from eth_account import Account
from larp.execution import Blocked
from larp.signer.keyfile import load_key_file
wallet = json.load(open('/etc/larp/signer.json'))['wallet_address'].lower()
try:
    material = load_key_file('/etc/larp/signer/wallet.key')
    if 'WALLET_MNEMONIC' in material:
        Account.enable_unaudited_hdwallet_features()
        address = Account.from_mnemonic(material['WALLET_MNEMONIC']).address
    else:
        address = Account.from_key(material['WALLET_PRIVATE_KEY']).address
    ok = address.lower() == wallet
    print(json.dumps(dict(key_loader='PASS', credential=sorted(material)[0], wallet_matches=ok)))
except Blocked as refused:
    print(json.dumps(dict(key_loader='REFUSED', reason=str(refused))))
    raise SystemExit(4)
if not ok:
    raise SystemExit('key file is for another wallet; remove it and stop')
PY
systemctl enable --now larp-signer.service
sleep 20
echo "larp-signer $(systemctl is-active larp-signer || true) restarts=$(systemctl show larp-signer -p NRestarts --value)"
# The start line is fixed JSON (started, swap_decoder, policy hash, deviation, cap_basis); never key material.
journalctl -u larp-signer --since "-2 min" --no-pager -o cat | grep -E '^\{' | tail -3 || true
echo S2_DONE
