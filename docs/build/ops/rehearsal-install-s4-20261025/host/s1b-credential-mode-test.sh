# S1b (signer, read-only for the key, after K1): prove systemd's LoadCredential copy of wallet.key passes the same
# loader the signer uses, running as larp-signer exactly like larp-signer.service (SJ-06-RV01). Prints the copy's mode,
# owner and the loader verdict only, never key material. Starts nothing; the transient unit is removed on exit.
set -euo pipefail
[[ -f /etc/larp/signer/wallet.key ]] || { echo "no key file; K1 first"; exit 3; }
out=$(systemd-run --quiet --wait --pipe --collect -p User=larp-signer -p Group=larp-signer \
  -p LoadCredential=wallet.key:/etc/larp/signer/wallet.key -p WorkingDirectory=/opt/larp/current \
  -p Environment=PYTHONDONTWRITEBYTECODE=1 \
  /opt/larp/current/.venv/bin/python -c '
import json, os, stat
from larp.execution import Blocked
from larp.signer.keyfile import load_key_file
p = os.path.join(os.environ["CREDENTIALS_DIRECTORY"], "wallet.key")
st = os.stat(p)
r = dict(copy_mode=oct(stat.S_IMODE(st.st_mode)), copy_owner_is_me=st.st_uid == os.geteuid())
try:
    m = load_key_file(p); r.update(key_loader="PASS", credential=sorted(m)[0]); del m
except Blocked as e:
    r.update(key_loader="REFUSED", reason=str(e))
print(json.dumps(r, sort_keys=True))
')
echo "$out"
grep -q '"key_loader": "PASS"' <<<"$out" || { echo "LoadCredential copy refused; stop before S2 (no S1B_DONE)"; exit 5; }
echo S1B_DONE
