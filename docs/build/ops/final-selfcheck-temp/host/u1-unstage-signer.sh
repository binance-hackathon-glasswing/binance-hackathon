# U1s (signer, host mutation; IDEA-110 TA-01): stop the refused 2aa95617 signer and move its configs aside for the
# e261bcfc install. The final wallet key stays at /etc/larp/signer/wallet.key (S1b/S2 check it again).
set -euo pipefail
umask 077
[[ -e /etc/larp/role-signer ]] || { echo "not the signer"; exit 3; }
grep -q '"run_id": *"larp-final-selfcheck-temp"' /etc/larp/signer.json || { echo "unexpected signer.json run"; exit 3; }
grep -q '"build_id": *"2aa95617bf9217455d88446f44c7cdbd8276f88b"' /etc/larp/signer.json || { echo "unexpected build"; exit 3; }
systemctl disable --now larp-signer.service 2>/dev/null || true
systemctl reset-failed larp-signer.service 2>/dev/null || true
state=$(systemctl is-active larp-signer || true); enabled=$(systemctl is-enabled larp-signer 2>/dev/null || true)
echo "larp-signer $state $enabled"
[[ $state != active && $state != activating && $enabled != enabled ]] || { echo "larp-signer still running or enabled"; exit 5; }
H=/etc/larp-history/2aa9561-larp-final-selfcheck-temp
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json signer.json untrusted-router-policy.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
stat -c '%a %U:%G %n' /etc/larp/signer /etc/larp/signer/wallet.key
echo U1S_DONE
