# P6 (primary, after P4 -> S2 -> P5): start planning only with a healthy executor.
set -euo pipefail
state=$(systemctl is-active larp-execution || true)
restarts=$(systemctl show larp-execution -p NRestarts --value)
[[ $state == active && $restarts == 0 ]] || { echo "executor is not healthy; runtime not started"; exit 5; }
systemctl start larp-runtime
sleep 30
for u in larp-runtime larp-execution; do
  state=$(systemctl is-active "$u" || true); restarts=$(systemctl show "$u" -p NRestarts --value)
  echo "$u $state restarts=$restarts"
  [[ $state == active && $restarts == 0 ]] || { echo "a service is not healthy; no P6_DONE"; exit 5; }
done
echo P6_DONE
