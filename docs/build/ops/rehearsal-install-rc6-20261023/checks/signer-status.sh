# Read-only (signer; needs the T1 SSM endpoints): unit state and the signer's fixed JSON status lines.
#   python3.12 -I ssm_run.py --signer checks/signer-status.sh
set -eu
echo "larp-signer $(systemctl is-active larp-signer || true) restarts=$(systemctl show larp-signer -p NRestarts --value)"
journalctl -u larp-signer --since "-30 min" --no-pager -o cat | grep -E '^\{' | tail -5 || true
stat -c '%a %U:%G %h %n' /etc/larp/signer /etc/larp/signer/wallet.key 2>/dev/null || echo "no key file"
