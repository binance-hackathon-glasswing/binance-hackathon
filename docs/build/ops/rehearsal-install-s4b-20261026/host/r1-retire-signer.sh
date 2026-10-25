# R1s (signer, host mutation, needs T1): retire the signer of run larp-dev-rehearsal-20261025-s4 (RC7 7fc9f60). Stops
# and disables larp-signer and moves (never deletes) signer.json, release.json and the router policy to
# /etc/larp-history/. The wallet key stays at /etc/larp/signer/wallet.key: the new run signs for the same dev wallet,
# so K1 is not repeated (S1b and S2 check it again). Prints no key material.
set -euo pipefail
RUN=larp-dev-rehearsal-20261025-s4; BUILD=7fc9f6019b54dccaf13b886c2e1123e703abf67a
[[ -e /etc/larp/role-signer ]] || { echo "not the signer"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/signer.json || { echo "unexpected signer.json run"; exit 3; }
systemctl disable --now larp-signer.service 2>/dev/null || true
sleep 3
state=$(systemctl is-active larp-signer || true); enabled=$(systemctl is-enabled larp-signer 2>/dev/null || true)
echo "larp-signer $state $enabled restarts=$(systemctl show larp-signer -p NRestarts --value)"
[[ $state != active && $state != activating && $enabled != enabled ]] || { echo "larp-signer still running or enabled"; exit 5; }
journalctl -u larp-signer --since "2026-10-23 17:00:00" --no-pager -o cat | grep -E '^\{' | grep -c '"started": true' \
  | sed 's/^/signer start lines since S2: /' || true
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json signer.json untrusted-router-policy.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
stat -c '%a %U:%G %h %n' /etc/larp/signer /etc/larp/signer/wallet.key
echo R1S_DONE
