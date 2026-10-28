# B1 (primary, read-only; IDEA-104 R3, FS1 sheet B1): the shared OpenAI budget ledger the routed runtime opens at
# /var/lib/larp-runtime/model-budget/openai-budget.sqlite. Read-only (sqlite mode=ro): no init, status or export here,
# because status/export advance the ledger clock (llm-trial sheet). If the ledger is absent, the owner initializes it with
# `model_budget init --routing-file /etc/larp/model-routing.json --account larp-openai-2026 --initial-spent-micro-usd
# <reconciled prior spend>` as larp-runtime (F0b, KMP-BUD01); the routing file requires the prior spend it pins.
#   ssm_run.py host/b1-model-budget-check.sh
set -euo pipefail
umask 077
L=/var/lib/larp-runtime/model-budget/openai-budget.sqlite
if [[ ! -f $L ]]; then echo "ledger absent: owner init needed (see header); no B1_DONE"; exit 4; fi
stat -c '%a %U:%G %n' "$L"
python3 -I - "$L" <<'PY'
import sqlite3, sys
c = sqlite3.connect('file:%s?mode=ro' % sys.argv[1], uri=True)
name, total, reserve = c.execute('SELECT name,total,reserve FROM account WHERE id=1').fetchone()
spent = c.execute("SELECT COALESCE(SUM(amount),0) FROM charges").fetchone()[0]
tables = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'"))
print('account=%s total_micro_usd=%d reserve=%d charged_micro_usd=%d tables=%s' % (name, total, reserve, spent, ','.join(tables)))
if name != 'larp-openai-2026':
    sys.exit('ledger account differs from the FS1 routing budget_account')
PY
echo B1_DONE
