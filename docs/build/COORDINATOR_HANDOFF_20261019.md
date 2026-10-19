# Coordinator handoff — 2026-10-19 (SGT)

Yao Zhu is stepping down as coordinator after the Oct 18 deployment. This page is the entry point for the next
coordinator. PR133 (`claude/pre-trading-checklist-20261017`, base `codex/system-testing-20261012`) stays OPEN and
carries the live checklist; this page and IDEA-066 hold the detail.

## 1. Read in this order

1. `AGENTS.md` → `docs/skill/SKILL.md` §0 (never-do list) → `docs/LEDGER.md` table.
2. This page.
3. `docs/ledger/IDEA-066.md`, sections **PC-DEPLOY01 / PC-FIX02 / PC-BUILD01 / PC-DEPLOY02** (bottom), and the
   machine-readable [deployment record](evidence/llm-trial-deployment-20261018.json).
4. `docs/build/PRE_TRADING_CHECKLIST.md` (one owner per line) and `docs/INCOMPLETE_WORK.md` (GAP-70/72).
5. Only when doing host work: [ops scripts README](ops/llm-trial-20261018/README.md), `docs/build/AWS_RUNBOOK.md`,
   `docs/build/runbook.md`, and the frozen 86b1476 `docs/build/DOJ_TRIAL_CAP_FIXES_20261018.md`.

## 2. What is running now (observed 2026-10-18 17:20 UTC)

| Item | Value |
|---|---|
| Host | `primary` `i-040fc5fea8b700e9a`, ap-southeast-2, AWS profile `larp` |
| Build | `ea25b52325656a19b29e8ddb07b94dd792be6e18` = merged PR178 (OpenAI JSON-input fix). **Local build, no CI** (Yao's decision); bundle `9c7ac630…`, manifest `fc3adfb4…`. Differs from Keegan's CI 86b1476 bundle only in `providers.py`, manifest, BUNDLE.env |
| Run | `larp-dev-llm-trial-20261018t170339z`, mode `dev`, execution `shadow` (no signing), activated epoch 2 by Yao Zhu |
| Database | `larp_trial2` on the existing RDS instance (IAM auth). Frozen earlier runs: `larp-dev-shadow-20261017` (bb46234) in `larp`; 86b1476 trial run in `larp_trial` |
| Assessor | `aiand_routed`, routing `/etc/larp/model-routing.json` SHA `a5fca50a…22d8d` (capped unsigned trial file): OpenAI `gpt-6.1-sol` medium primary; AIand Kimi K3 / GLM 5.3 high reviews/fallback |
| Budget ledger | `/var/lib/larp-runtime/model-budget/openai-budget.sqlite`, one ledger shared by all runs. US$50 total, US$2 prior, no reserve, pacing ≈US$1.85/day; trial `larp-unsigned-v3-20261018` < US$8 total, < US$2.50/UTC day, ends **2026-10-22 00:00 UTC** (never move it). Holds one **UNKNOWN 84,764 µUSD** charge from the 86b1476 bug (kept). Backup `openai-budget-20261018T170220Z.sqlite` `2a20adc1…` |
| Services | `larp-evidence`, `larp-runtime`, `larp-uploader`, `larp-archive.timer` active; `larp-execution` disabled. Signer host not provisioned |
| First fixed job | `cadence:1991492#1` 17:15Z: OpenAI ASSESSED, charges SETTLED; Kimi ABSTAIN; GLM still running at the deadline → **combined UNAVAILABLE (`ASSESSMENT_DEADLINE_EXCEEDED`, 60 s)**; receiver `STORED` |

## 3. Access and private inputs (not in Git)

- **AWS:** only Yao Zhu had working `larp` profile access (`aws login --profile larp --region ap-southeast-2`). The new
  coordinator must get access from the account owner, or ask Yao to run host steps. No Terraform apply or new spend
  without the account owner's explicit OK.
- **Private files on Yao's Mac**, needed for any new prepare/redeploy, to be handed over privately (never Git, chat or
  issues): `deploy/activation/tf-output.json` (Terraform outputs), repo-root `.env` (Web3 keys for the capture),
  `deploy/activation/balance-rpc/selected-providers.json` (private RPC URLs),
  `deploy/activation/gate-a-prepared-20261017/{runtime.json,evidence.env}` (wallet address, SEC contact),
  `deploy/activation/interim-20261017/profiles/rehearsal-live.json` (interim profile `d951207f…`), the original/verified
  bundles under `deploy/activation/{pr174-verification,redeploy}-20261018/`, and private SSM results/labels in
  `deploy/activation/` and `~/Downloads/LARP-*`.
- **Secrets** live in Secrets Manager (`larp-dev/runtime` holds both model keys; `larp-dev/uploader`). Do not replace
  them without diagnosing first. The RDS admin secret is read only by the owner's port-forward script.
- **Claude sessions:** the auto-mode permission classifier blocks Claude from AWS/RDS/host writes and from reading
  `tf-output.json`; Claude writes scripts and the operator runs them. Claude's read-only SSM checks work.

## 4. Watching the running trial

Read-only checks (copy `ops/llm-trial-20261018/` into ignored `deploy/activation/` first):
`checks/host-health.sh` (units, latest source polls, operations health, audit/anchor/backup status),
`checks/assessment-status.sh` (each round's stages/status/reasons), `checks/first-round-detail.sh` (ledger charges,
model artifacts, receiver ACKs). Watch: K1–K4 and headroom incl. in-flight/UNKNOWN reservations; AIand balance (only
owner-reported 140+; balance endpoint 403); DOJ polls after the fix; audit chunks all `ACK`; hourly anchors and the
00:00 UTC daily backup. `model_budget status`/`export` advance the ledger clock: they are owner actions, not
read-only checks. Never reset, edit or re-initialize the ledger; never delete a run, journal or archive object.

## 5. Calendar (UTC)

| When | What | Owner |
|---|---|---|
| Oct 19–22 00:00 | Unsigned trial window; actual start = first qualified job, not the window start | Keith (report), coordinator (ops) |
| Oct 20 morning | Keith interim report; Keegan decides the bounded signed rehearsal; final measured profile replaces the interim one | Keith, Keegan |
| Oct 20 | Profile swap = new prepare/bind/init/activate: **needs a new database `larp_trial3`** (or reviewed version-switch support first). Use the ops scripts | coordinator + AWS operator |
| Oct 21 00:00 – Oct 22 00:00 | Signed rehearsal buy window, only if Gate B passes (signer, router/source, caps #44) | Isaac, Keegan, operator |
| Oct 22 | Close the unsigned window: last job, cutoff, budget reconciliation, verdict (TRB-01A); freeze routing/prompts | Keith |
| Oct 27–29 | Final activation with a **fresh final wallet** (new run, likely new ai-seeds secret) | team |
| Oct 29 – Nov 12 | Scored run: no human changes (F-114/F-117) | — |

## 6. Open items and owners (all also on PR133)

| Owner | Item |
|---|---|
| Keegan (code/release review) / Keith (protocol/affordability) | Isaac implemented IDEA-083 at the user's request in [PR181](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/181), stacked on179/180. Final local PG14 suite2079 passed/9 platform-external skips/3272 subtests, plus14 expanded components/257 subtests (PC-IMPL18101). B11/180s/parallel review/DEV-22 and linked primary identity are implemented; prompts/efforts/pinned routing unchanged. PR179/180/181/182 are now merged. Remaining: exact Linux/systemd/original release qualification (PR183; org CI billing-blocked #98), Keith cost/protocol review, then coordinator/operator install and actual stage timings/charges/receiver ACK. No AWS/deployment/key change by this session; preserve ledger, existing adoption and Gate B prerequisites. |
| Keegan | Review merged PR178 and the local non-CI ea25b52 build; reviewed version-switch support (one run per wallet); include merged PR177/176 in the exact next reviewed release; Gate A/B review; B4 `exposure_evidence` producer; DEV20 planner disposition |
| Account owner / coordinator | Reconcile the one UNKNOWN 84,764 µUSD charge (reviewed; never edited); AIand units/expiry/funding; owner `status`/`export` snapshot with hashes; delete S3 transfer copies `releases/llm-trial-20261018t160739z/` and `releases/llm-trial-20261018t170339z/` (`mac/r9-cleanup-s3-package.sh`); confirm who created `larp_trial` before the first recorded setup |
| Coordinator | Post-fix DOJ polls/restart and a NEW observed-window `report --coverage-scope current`; original fixed 24 h report stays FAIL; historical PERMANENT backup failure stays recorded. PC-LABEL02-INJ01 local trust review/regressions delivered under [PC-YAO-NB01](YAO_NONBLOCKING_REVIEW_20261019.md); Keegan's independent review remains. YP-01 supplies the original interim summary/provenance for Keith. |
| Keith | Measured final profile/parameters, usage/affordability, actual unsigned population, blind labels, M9, trial report. Short windows and signed hours never count toward the 72 unsigned hours |
| Isaac | Real router/source/ABI/replay/native provider, signer/caps/funding evidence; signed approve+swap/ACK/crash/restore drills with the host operator |

The withdrawn "4/10" rating stays withdrawn; the small AI-labelled deterministic diagnostic qualifies neither T01 nor
v3 M9. Signed-trading gates are separate from everything above.

MERGE-RV20261019 update: Isaac reviewed and merged177/176 into integration
and171/173 into PR133 under the user's instruction. This tracker includes the
updated integration base and remains OPEN. Evidence and remaining release/host/
source/caps/model-contract gates: IDEA-066 MERGE-RV20261019 and the live checklist.
No deployment or AWS/key operation follows from repository merges.

PC-SIGNER-ASSEMBLY01 (Oct19): PR179/180/181/182 are now merged; PR133 includes
integration8c1e6df via cabc159. Code reconciliation is complete. PR183 contains
release-declaration alignment and separate exact-release qualification; review
and host acceptance remain distinct. New [PR184](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/184)
delivers the offline signer installation-candidate assembler and procedure,
194 tests/349 subtests/0 skips PASS. It is stacked on133 for review, not installed.
Actual assembly still needs source-reviewed evidence, measured profile/fresh
full holdings/top-up/fee quotes, #44 acceptance, #27 finite policy/code/timing,
and the operator's signed run/release/DB/CA bindings. See the checklist's current
PC-SIGNER-ASSEMBLY01 owner rows. The old draft stays unchanged/uninstallable;
all generated reports keep installation/signing/Gate B false. No AWS or keys.


PC-CONT01 update (2026-10-19): PR184's offline assembler is independently reviewed
and merged into PR133 (SA-RV01:194 tests/349 subtests, no skips); real assembly is
still NOT_RUN_MISSING_INPUTS. PR183 is merged into integration and its evidence
is reconciled here: original candidatec5be269 is published/qualified under
AB-REL01. See PRE_TRADING_CHECKLIST.md PC-CONT01 and the candidate release README.
The frozen release predates the new assembler; run that preparation tool from
the reviewed checkout when real inputs arrive. Host installation, preserved
ledger state, actual timing/charges/ACK, numeric/source/native/#27/#44 and the
approved signer session remain separate. No host or key action occurred.


PC-CONT01 acceptance: combined source9a0b80e passes all4 mirror39213335253 jobs,
2109 tests/3340 subtests/6 expected skips, separate real systemd5/5. PR126 briefs
are aligned and included in the tracker after doc checks; application bytes
are unchanged by that follow-up. Refer to the machine receipt
`evidence/pr133-continuation-20261019.json` and current checklist for limits.
No host result, real assembly or later contents are attributed to frozenc5be269.
