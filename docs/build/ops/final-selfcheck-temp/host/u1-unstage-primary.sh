# U1p (primary, host mutation; IDEA-110 TA-01): move the never-activated 2aa95617 temp configs aside so the e261bcfc
# release and package can be installed. The quarantined run and larp_final_selfcheck stay; nothing was started.
set -euo pipefail
umask 077
grep -q '"run_id": *"larp-final-selfcheck-temp"' /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"build_id": *"2aa95617bf9217455d88446f44c7cdbd8276f88b"' /etc/larp/runtime.json || { echo "unexpected build"; exit 3; }
for u in larp-execution larp-runtime larp-uploader larp-evidence larp-archive.timer; do
  [[ $(systemctl is-active $u || true) != active ]] || { echo "$u is active; refusing"; exit 3; }
done
H=/etc/larp-history/2aa9561-larp-final-selfcheck-temp
[[ ! -e $H ]] || { echo "history dir already exists; not overwriting"; exit 3; }
install -d -m 0750 -o root -g root /etc/larp-history "$H"
for f in release.json runtime.json operations.json uploader.json execution.json initial-state.json strategy-profile.json \
         session-calendar.json evidence.env registration-evidence.json untrusted-router-policy.json model-routing.json token-history.json; do
  if [[ -f /etc/larp/$f ]]; then mv -n "/etc/larp/$f" "$H/$f"; fi
done
(cd "$H" && sha256sum *)
ls /etc/larp
echo U1P_DONE
