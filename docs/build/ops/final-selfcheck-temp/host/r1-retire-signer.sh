# R1s (signer, host mutation, needs T1): retire the signer of dev run larp-dev-rehearsal-20261027-s5-cost01 (3ae83098).
# Stops and disables larp-signer and moves (never deletes) signer.json, release.json and the router policy to
# /etc/larp-history/. The DEV wallet key also moves there (root-only, never printed): this run signs for the final
# wallet, so Isaac places the final wallet's key at /etc/larp/signer/wallet.key (K1) before S1b and S2.
set -euo pipefail
umask 077
RUN=larp-dev-rehearsal-20261027-s5-cost01; BUILD=3ae830981b9ce1c4b80a46dbeb086825d91ae7ec
[[ $(readlink -f /opt/larp/current) == /opt/larp/releases/$BUILD ]] || { echo "unexpected source release; refusing retirement"; exit 3; }
[[ -e /etc/larp/role-signer ]] || { echo "not the signer"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/signer.json || { echo "unexpected signer.json run"; exit 3; }
systemctl disable --now larp-signer.service 2>/dev/null || true
sleep 3
state=$(systemctl is-active larp-signer || true); enabled=$(systemctl is-enabled larp-signer 2>/dev/null || true)
echo "larp-signer $state $enabled restarts=$(systemctl show larp-signer -p NRestarts --value)"
[[ $state != active && $state != activating && $enabled != enabled ]] || { echo "larp-signer still running or enabled"; exit 5; }
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json signer.json untrusted-router-policy.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
if [[ -f /etc/larp/signer/wallet.key ]]; then
  install -d -m 0700 -o root -g root "$H/dev-key"
  mv -n /etc/larp/signer/wallet.key "$H/dev-key/wallet.key"
  [[ ! -e /etc/larp/signer/wallet.key ]] || { echo "dev key still in place"; exit 5; }
  echo "dev wallet key moved to $H/dev-key (root-only)"
fi
stat -c '%a %U:%G %n' /etc/larp/signer
echo R1S_DONE
