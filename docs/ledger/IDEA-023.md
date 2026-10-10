# IDEA-023 — Start the engine with an offline policy boundary

- Date / author: 2026-10-10 / Codex, requested by Keegan (start building on the reviewed version; continue development).
- Status: open; first implementation increment of IDEA-021 W01 and test-discovery setup from W09. Not an adopted trading policy or activation authorization.
- Basis: reviewed `3cb8765`, plus review record `9fe13b1`; branch `codex/engine-foundation`.
- What: immutable canonical documents, version-bound decision snapshots and policy state, explicit KEEP_QUANTITY/TARGET_WEIGHT/EXIT proposals, and deterministic validation. Offline synthetic tests import no probes, credentials or network adapters.
- Why: give later storage, risk, policy and execution work one explicit boundary without choosing unresolved exposure/evidence policies.
- Cost / risk: no order creation, signing, credential access or API calls. No dependency or strategy-parameter changes. Contracts alone are not a security sandbox or a complete engine.
- Links: IDEA-021 ENG-02, W01/W09, AT01/AT03/AT20; GAP-65. Research corrections remain GAP-66.

## 1. Implementation decisions

- Canonical document v1: UTF-8 JSON, sorted string keys, compact separators, integer-only JSON numbers. Nested input is copied into immutable bytes; reading produces a detached copy. Raw bytes must already be canonical, rejecting duplicate keys and alternate encodings. No claim of compatibility with the separate ai-seeds wire format.
- Weight instructions use exact `Fraction` values, serialized as numerator/denominator pairs. Float, NaN, Infinity, negative and above-one weights are rejected. Explicit weight sum cannot exceed one. This is structural validation; existing KEEP holdings and independent portfolio caps need the later risk/planning layer.
- Snapshot identity binds run/wallet/build/profile, event sequence, UTC observation time, universe, policy-state identity/version and context. Proposal identity binds its snapshot, policy, expiry, targets and proposed next state. Target ordering does not change the semantic proposal hash.
- Missing symbols become KEEP_QUANTITY. Validation never changes holdings or persists proposed state. Proposed next state belongs to the same run/policy/schema with exactly one version increment; durable compare-and-set and fill observations remain separate work.
- Context is an opaque canonical document in this first increment. Typed portfolio, pending-action, provenance/health/risk schemas, complete PolicySpec, review jobs, reducer, ports and isolated policy runner remain W01/W03/W05 work. No claim that arbitrary context satisfies the complete ENG-02 snapshot contract.
- `pytest.ini` defaults discovery to `tests/test_*.py`, avoiding credential-dependent `binance_test.py` and research probes. The checks also run with standard-library unittest, with no new dependency installation.

## 2. Prospective verification criteria

Before any new decision-related code runs, commit and push implementation, tests and these criteria as AGENTS.md requires. These are engineering unit checks, not a market or policy experiment.

Pass only if:
1. Canonical ordering/Unicode yields stable bytes and domain-specific hashes; nested mutation of source or returned copies cannot change stored state.
2. Noncanonical/duplicate-key documents, mutable snapshot members, naive times and malformed counters/profiles are rejected.
3. Changing event sequence, wallet/build/profile, context or state version invalidates old proposals; mismatched policy/state ownership also fails.
4. Missing targets keep quantities; explicit exits remain distinguishable; validation leaves balances and current policy state unchanged.
5. Invalid weights, duplicate/unknown targets and total explicit weight above one fail; exact rational weights and reordered targets are deterministic.
6. Expiry is exclusive: at or after expiry fails; time before snapshot observation fails; equivalent timezone representations produce the same snapshot hash.
7. Secret-free unittest discovery passes; if pytest is available, default collection includes only this suite and passes without importing `binance_test.py`. Whitespace checks pass.

## 3. Results and remaining work

Tests NOT RUN at initial commit. Results will be appended after the pushed implementation is tested. Full AT01, AT03 and AT20 remain incomplete: policy isolation, risk fallback/incident recording, durable state, Linux deployment and rehearsal are not delivered by these unit checks.

Next delivery: Yao Zhu / reviewer Keith owns the remaining W01 typed contracts, policy interface and reducer; Keegan / reviewer Isaac owns W02 atomic persistence and W09 environment/CI; Keith owns independent risk/accounting integration; Isaac owns execution. These remain the suggested allocation in IDEA-021, subject to GAP-37 availability. GAP-65 stays open; no readiness gate is closed by this increment.
