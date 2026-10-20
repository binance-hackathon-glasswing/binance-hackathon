# PC-AUDIT01 — captured trial and current-code audit (2026-10-20)

Requested by Yao: analyze the preserved unsigned trial, assess system performance,
and identify inconsistencies/unwanted behavior that remain after newer merged
LLM changes. Current comparison baseline is canonical commit
`697ff3a` (`origin/codex/system-testing-20261012` at audit start); captured
runtime is `ea25b52325656a19b29e8ddb07b94dd792be6e18`.

Prospective audit criteria (before replay / scoring):

- A1: verify the private final export's file manifest and Backup.v1 digest; independently
  recompute all journal batch/event/head hashes and terminal projection; reconcile
  rounds, audit payloads/chunks/ACKs and zero execution/signing rows.
- A2: join all captured assessments, stage results, original request/reply/tool
  artifacts and evidence sources. Check point-in-time cutoffs, provenance,
  model/effort identity, tool/stage limits and accepted unsupported content.
- A3: measure availability/latency/status/coverage/duplication by issuer and
  route with honest denominators. Replay the same immutable requests through
  the deterministic baseline offline where reconstructable; missing evidence
  remains missing. Apply existing frozen protocol definitions, never tune them.
- A4: reconcile OpenAI ledger entries, recorded usage and unmetered/late calls;
  distinguish known costs, conservative reservations and unavailable invoices.
- A5: inspect each candidate defect against the latest merged code and existing
  regression evidence. Exclude already-fixed behavior from remaining findings.
  Reproduce remaining candidates offline with real captured inputs where possible.
- A6: retain source/model/label data and per-case audit details privately; publish
  aggregate measurements, exact source/data hashes, concrete remaining findings
  and confidence/limits. No paid inference, AWS mutation, trading or deployment.

This is a retrospective engineering audit, not a new blind-label experiment.
No independent accuracy/profit or absence-of-all-defects claim is possible from
an unsigned two-issuer capture. Existing trial sampling/labels/adoption gates stand.
