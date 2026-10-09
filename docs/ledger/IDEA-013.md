# IDEA-013 — Review of pulled changes and funding readiness

- Date / author: 2026-10-09 / Codex, requested by Keegan.
- Status: open; review recommendations, not strategy adoption or trading authorization.
- Scope: pull from `ab4143f` to `1fc7574` (16 commits); static review of all three changed Python tools, the new direction proposals and their cross-references. No claim to have independently reproduced the market measurements, literature review, simulations or source-rights research in IDEA-008..012.
- Why: identify implementation and specification defects before the funded development rehearsal.
- Cost / risk: local source/document review only. No credential files read, network probes run, ai-seeds logs uploaded, transactions signed or funds moved.
- Links: IDEA-009..012; GAP-12, GAP-24, GAP-26, GAP-29, GAP-31, GAP-41, GAP-44, GAP-46, GAP-47, GAP-50, GAP-63.

## 1. Team update and current readiness

**TU-01 [TEAM STATEMENT, Keegan, 2026-10-09]:** “We already have access to the secret key and money is entering tmr.” Tomorrow is **2026-10-10 SGT**. Record secret access as reported; the message does not independently establish which credential is meant, its deployment on every host, address binding, or successful ai-seeds authentication. No secret value was requested or inspected. This supersedes waiting for access as the working assumption; the remaining step is validating the required credentials through the versioned startup path.

Funding is expected on Oct 10, not observed in this review. F-116's historical organiser statement “by Oct 11” remains intact. Confirm the actual organiser-funded USDT and usable BNB after arrival; Q-03 is not closed by an expected deposit. Do not infer that the wallet is ready to sign from secret access alone.

The checked-out non-vendored Python files are research/probe tools and `binance_test.py`. No production agent, signer gate, durable execution journal, recovery implementation or automated test suite is present in this checkout. External/unmerged work was not inspected. IDEA-009..012 remain proposals, with competing sizing, authority and risk choices. Funds arriving does not implement GAP-29..34 or GAP-46/47.

## 2. Actionable findings

Priorities describe the consequence **if a proposed specification is implemented**; these are not claims that a live agent currently has these defects.

### R1 [P1] Integrity failures must block exits as well as buys

**Location:** IDEA-010 §5 item 12 (and §4 T.1). Item 12 explicitly permits exits to continue after version mismatch, address mismatch or an unknown outgoing transaction/nonce gap. An exit still signs a wallet transaction: it cannot bypass G-03, G-09 or G-18. A version mismatch would allow the wrong build to trade; unresolved wallet/nonce state can cause conflicting execution. Separate discretionary entry halts from a hard signing halt. Risk exits bypass profitability/entry filters only; they still need verified identity, version, economic payload and reconciled wallet state. Owner suggestion: Keith + Keegan; GAP-12/GAP-31.

### R2 [P1] Keep recipient and minimum-output verification mandatory

**Location:** IDEA-011 X9 and §4 agenda item 5. Making recipient decoding conditional on ABI availability weakens the current G-01 MUST. An allowed router and selector plus a favorable JSON `minReceiveAmount` do not prove that the signed calldata sends the purchased asset to our wallet or enforces that minimum output. Preserve the activation blocker until the actual payload can be validated, or document and verify an equivalent binding guarantee. A missing ABI is unresolved engineering work, not evidence that the checks are unnecessary. This is an existing team guardrail, not a claim that the organisers prescribe a particular decoder. Owner suggestion: Keith; GAP-29.

### R3 [P1] An LLM-round timestamp is not a filing-ingestion watermark

**Location:** IDEA-012 §8.1 N1; also IDEA-010 §4 L.1. Filtering for `acceptanceDateTime` after the previous LLM round loses filings published before that round but discovered later. Example: filing accepted 11:59, a 12:00 round runs while EDGAR is unavailable, and the filing is first fetched at 12:05; the next round rejects it forever. Use a durable per-source ingestion cursor with an overlap/backfill window and accession-ID deduplication; advance only after successful retrieval and durable queuing. Track assessed IDs separately and retain pending work across model failures. Owner suggestion: Yao Zhu + Keegan; GAP-24/GAP-28.

### R4 [P1] The newest LLM schema reintroduces trade authority

**Location:** IDEA-012 §8.3 L2 and §8.4 R-VOTE. The model chooses HOLD / EXIT / ENTER and a 4-of-5 vote determines which posture is acted on. Deterministic sizing after the vote does not remove the model's directional trade authority. The submitted architecture says “LLM zone: authority over evidence only, never over trades” and “output schema cannot express a trade.” IDEA-010 §1 already corrected this problem, but IDEA-012 reintroduces it while claiming evidence-only authority. Keep a structured evidence-assessment schema and a separately declared deterministic action map, or explicitly decide and record the design deviation before adoption. Owner suggestion: Yao Zhu + team; D-11/GAP-62.

### R5 [P2] EDGAR text extraction concatenates adjacent table cells

**Location:** `tools/edgar_fetch.py`, `_Text.BLOCK` and `html_to_text`. There are row separators but no `td`/`th` separators. For valid compact HTML such as `<tr><td>Revenue</td><td>100</td><td>90</td></tr>`, `handle_data` appends the cells and `"".join(p.out)` produces `Revenue10090`. Financial tables can therefore change the apparent numeric evidence supplied to the model. Preserve cell boundaries (and enough row/header context for comparison); cover compact HTML with an extraction fixture before using this text for numerical claims. Owner suggestion: Yao Zhu; GAP-24/GAP-26.

### R6 [P2] EDGAR saved-text encoding is platform dependent

**Location:** `tools/edgar_fetch.py`, `(out / "docs" / fname).write_text(text)` and `text_sha256`.
The file is written using the locale default while its hash is computed over UTF-8. Under a Windows non-UTF-8 locale, representable non-ASCII text has different saved bytes and hash; other characters raise `UnicodeEncodeError` before the final report is saved. Windows newline translation can also change the saved bytes relative to `text.encode()`. Write explicit UTF-8 bytes and hash those same bytes (or explicitly distinguish a normalized-text hash from a file hash). The record currently gives no such distinction. Owner suggestion: Yao Zhu; GAP-24.

### R7 [P2] The quote probe misdiagnoses authentication failures as host refusal

**Location:** `tools/probe_quote.py`, signed-read branch `code == COMPLIANCE_CODE or status in (401, 403)`.
This repeats IDEA-011 X11a and remains unfixed. The kit lists 401 signature/timestamp failures. The probe instead recommends another host and skips its clock check. Distinguish compliance code 40304 from authentication/permission errors; retain the API code and diagnostic clock information. Owner suggestion: Keegan; GAP-63.

### R8 [P2] A valid HTTP-date Retry-After crashes the quote probe

**Location:** `tools/probe_quote.py`, `int(resp.headers.get("Retry-After", 2 ** attempt))`.
`Retry-After` can contain an HTTP date; parsing it as an integer raises rather than honoring backoff. This is IDEA-011 X11c, still unfixed. Parse both delay and date forms, use a bounded fallback for invalid values, and preserve collected results on failure. Owner suggestion: Keegan; GAP-63.

## 3. Verification plan and limits

Checks specified before execution: parse the three changed Python files with `ast.parse` without importing them; require all three to parse. Run `git diff --check`; require no whitespace errors. Verify only the intended documentation files changed and no secret/data files are staged. These are syntax and documentation checks, not a research experiment or evidence of runtime readiness. No probe execution, model calls or trading tests are authorized by this review record.

R1–R8 are source-level findings with explicit triggering conditions; no mocked or live execution result is claimed. The table-cell and encoding examples are derived from the source. End-to-end behavior, credentials, balances, quote costs, off-hours trading state and SDK delivery remain untested here.

Source checks: extracted the submitted architecture PDF with pypdf; read relevant verbatim `docs/official/source_page.md` and `docs/official/kit/bstocks-trading-guide.md` passages alongside SKILL.md F-60..64, F-92..105, G-01/G-03/G-18 and Q-03/Q-16/Q-40, and participant-kit.md K4/K7/K8. The live organiser page and external financial/legal/literature claims were not re-verified; this review does not adopt them.

## 4. Remaining work and ownership

- Before funded transactions: Keith (suggested execution owner) and Keegan (suggested audit owner) implement and verify the versioned wallet checks, payload validation, journal, recovery and round-log path (GAP-29..34, GAP-46/47). Confirm actual funding and gas (GAP-41/Q-03). Existing ownership remains subject to GAP-37.
- Before adopting a strategy: team resolves the competing IDEA-010..012 directions, risk precedence and R1–R4; record decisions in D-11/D-12 and deviations in GAP-62. No strategy was adopted in this review.
- Research readiness: Isaac (suggested) collects quote/open-state evidence (GAP-44/GAP-50); Yao Zhu (suggested) resolves R3/R5/R6; Keegan (suggested) resolves R7/R8. GAP-63 tracks these review findings; no completed backlog item is claimed.

## 5. Verification results

- 2026-10-09: all three changed Python files passed `ast.parse` without imports or execution. `git diff --check` passed. Only IDEA-013, its ledger row and the live backlog were changed; no application code, credentials or datasets were changed. Review findings remain open, with suggested owners in §4 and GAP-63. No runtime-readiness claim follows from these checks.
