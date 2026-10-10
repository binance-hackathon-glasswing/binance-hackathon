"""Bounded evidence agent: assess(AssessmentRequest.v1) -> AssessmentResult.v1.

Loop (G-50 budget, at most 6 tool calls and 60 s, <= 3 tool types):
1. Validate identities, budget, tool allowlist, context hash and point-in-time evidence refs.
2. Load the referenced filings' primary documents and 8-K item metadata; extract facts.
3. The harness computes open gaps (unloaded exhibit, unknown prior comparison point,
   uncompared pair). The model chooses: call one allowlisted tool, or finish with claims.
4. Every claim is verified against the exact saved text. Unsupported claims, conflicting
   reported values or invalid model output cause abstention; timeouts/errors are UNAVAILABLE.
5. Compare with previously available context, detect novelty and contradictions, evaluate
   thesis falsifiers, propose the next thesis version and request later reassessment.

The deadline is enforced, not only measured: the assessment (evidence reads, tools and model
steps) runs in a worker thread that is abandoned at the deadline with an UNAVAILABLE result.
The abandoned worker makes no further model or tool call and its late output is discarded.

The result has no trade field at any depth. Confidence is an uncalibrated ordinal label,
never a probability. UNAVAILABLE and ABSTAIN results never propose a thesis update, and
the gate (gate.py) never lets them make evidence look clear. `completed_ms` is when the
result existed (feature availability); `cutoff_ms` is the evidence observation time.
"""

import threading

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, assert_no_trade_fields, digest, is_hash
from larp.intelligence import lifecycle
from larp.intelligence.facts import METRIC_NAMES, is_statement, issuer_names, statement_event, values_agree
from larp.intelligence.semantics import finding_eligible
from larp.intelligence.tools import (
    STATEMENTS, EvidenceIndex, ToolError, check_allowlist, comparable_pairs, load_document, load_items, run_tool,
)
from larp.intelligence.models import parse_output
from larp.intelligence.verify import detect_conflicts, fact_as_claim, verify_claim

EMPTY_CONTEXT = {"thesis": None, "known_facts": []}
STATUSES = ("ASSESSED", "ABSTAIN", "UNAVAILABLE", "REJECTED_REQUEST")
RESULT_SCHEMA = "AssessmentResult.v2"  # v2 (IDEA-031): event_statements, retained_facts, coverage replace
# v1's hypothetical_events; findings come only from re-verified issuer occurrences.


def context_hash(context: dict) -> str:
    return digest("larp.intel.context.v1", context)


class _State:
    def __init__(self, entry, index, config, cutoff, allowed_tools, context):
        self.entry, self.index, self.config, self.cutoff = entry, index, config, cutoff
        self.allowed_tools = allowed_tools
        self.texts, self.loaded, self.facts = {}, set(), {}
        self.current_records, self.prior_fact_ids, self.comparisons = [], set(), {}
        self.queried_prior, self.compared_metrics, self.injection, self.attempted = set(), set(), set(), set()
        self.tool_calls, self.tool_results, self.missing = [], [], []
        self.history_complete = {}
        self.coverage = {"documents_loaded": 0, "chars_loaded": 0, "documents_truncated": [], "facts_truncated": 0,
                         "statements_truncated": 0, "prior_records_scanned": 0, "prior_records_truncated": 0,
                         "statement_comparisons": 0, "statement_comparisons_truncated": 0,
                         "model_input_truncated": False, "model_input_chars_max": 0}
        self.context_facts = [f for f in context["known_facts"]
                              if f.get("source", {}).get("available_ms", self.cutoff + 1) <= cutoff]
        for fact in self.context_facts:
            self.facts.setdefault(fact["fact_id"], fact)

    @property
    def current_accessions(self) -> set:
        return {self.index.all_by_id[r]["accession"] for r in self.current_records}

    def current_facts(self) -> list:
        accessions = self.current_accessions
        return sorted((f for f in self.facts.values() if f["source"].get("accession") in accessions),
                      key=lambda f: f["fact_id"])

    def prior_facts(self) -> list:
        ids = self.prior_fact_ids | {f["fact_id"] for f in self.context_facts}
        accessions = self.current_accessions
        return sorted((self.facts[i] for i in ids if i in self.facts
                       and self.facts[i]["source"].get("accession") not in accessions), key=lambda f: f["fact_id"])

    def unread_exhibits(self) -> list:
        out = []
        for record_id in self.current_records:
            record = self.index.all_by_id[record_id]
            for doc in record["documents"]:
                if doc["role"] == "EXHIBIT" and (record["accession"], doc["name"]) not in self.loaded:
                    out.append((record["accession"], doc["name"]))
        return out

    def gaps(self) -> list:
        out = [{"gap": "EXHIBIT_NOT_LOADED", "tool": "fetch_document", "args": {"accession": a, "name": n}}
               for a, n in self.unread_exhibits()]
        metrics = [m for m in METRIC_NAMES if any(
            f["metric"] == m and f["kind"] in ("REPORTED", "GUIDANCE") and f["period"] for f in self.current_facts())]
        for metric in metrics:
            if metric not in self.queried_prior:
                out.append({"gap": "PRIOR_UNKNOWN", "tool": "prior_context", "args": {"metric": metric}})
        if STATEMENTS not in self.queried_prior and any(is_statement(f["metric"]) for f in self.current_facts()):
            out.append({"gap": "PRIOR_UNKNOWN", "tool": "prior_context", "args": {"metric": STATEMENTS}})
        for metric in metrics:
            if metric not in self.compared_metrics and comparable_pairs(self, metric):
                out.append({"gap": "UNCOMPARED", "tool": "compare_facts", "args": {"metric": metric}})
        return [g for g in out if (g["tool"], Document.from_dict(g["args"]).payload) not in self.attempted]

    def view(self, gaps, remaining_calls) -> dict:
        """Model input. Bounded by `max_model_input_chars` (a token proxy): prior facts, then tool results, then
        document excerpts are cut, in that order, and the cut is recorded as incomplete coverage."""
        limit = self.config.limits["max_tool_result_chars"]
        view = self._view(gaps, remaining_calls, limit)
        cap = self.config.limits["max_model_input_chars"]
        size = len(Document.from_dict(view).payload)
        if size > cap:
            self.coverage["model_input_truncated"] = True
            for key in ("prior_facts", "tool_results"):
                view[key] = view[key][: max(0, len(view[key]) // 4)]
            view["documents"] = [dict(d, excerpt=d["excerpt"][: limit // 4]) for d in view["documents"]]
            size = len(Document.from_dict(view).payload)
        self.coverage["model_input_chars_max"] = max(self.coverage["model_input_chars_max"], size)
        return view

    def _view(self, gaps, remaining_calls, limit) -> dict:
        return {"issuer": {"issuer_id": self.entry.issuer_id, "entity_name": self.entry.entity_name,
                           "filer_class": self.entry.filer_class},
                "cutoff_ms": self.cutoff, "allowed_tools": list(self.allowed_tools),
                "remaining_tool_calls": remaining_calls, "gaps": gaps,
                "documents": [{"text_sha256": sha, "excerpt": text[:limit], "chars": len(text)}
                              for sha, text in sorted(self.texts.items())],
                "facts": self.current_facts(), "prior_facts": self.prior_facts(),
                "tool_results": self.tool_results,
                "claimable": [fact_as_claim(f) for f in self.current_facts()]}


class EvidenceAssessor:
    """Implements the shared Assessor port: assess(request: Document) -> Document."""

    def __init__(self, *, registry, reader, model, config, clock_ms):
        self.registry, self.reader, self.model, self.config, self.clock = registry, reader, model, config, clock_ms

    # ------------------------------------------------------------------ request
    def _validate(self, r: dict):
        def need(condition, code):
            if not condition:
                raise IntelligenceError(code)
        need(r.get("schema") == "AssessmentRequest.v1", "SCHEMA")
        for key in ("job_id", "run_id", "issuer_id"):
            need(type(r.get(key)) is str and r[key] and r[key].strip() == r[key], f"MISSING_{key.upper()}")
        need(any(e.issuer_id == r["issuer_id"] for e in self.registry.entries), "UNKNOWN_ISSUER")
        entry = self.registry.by_issuer(r["issuer_id"])
        cutoff = r.get("cutoff_ms")
        need(type(cutoff) is int and cutoff >= 0, "CUTOFF_MALFORMED")
        need(cutoff <= self.clock(), "CUTOFF_IN_FUTURE")
        need(is_hash(r.get("policy_profile_hash")), "POLICY_PROFILE_HASH_MALFORMED")
        need(is_hash(r.get("context_hash")), "CONTEXT_HASH_MALFORMED")
        context = r.get("context", EMPTY_CONTEXT)
        need(type(context) is dict and set(context) == {"thesis", "known_facts"}
             and type(context["known_facts"]) is list, "CONTEXT_MALFORMED")
        need(r["context_hash"] == context_hash(context), "STALE_OR_MISMATCHED_CONTEXT_HASH")
        budget = r.get("budget") if type(r.get("budget")) is dict else {}
        calls, deadline = budget.get("tool_calls"), budget.get("deadline_ms")
        need(type(calls) is int and 0 <= calls <= self.config.max_tool_calls and type(deadline) is int
             and 0 < deadline <= self.config.max_deadline_ms, "BUDGET_EXCEEDS_DECLARATION")
        try:
            tools = check_allowlist(r.get("allowed_tools"), self.config.tools)
        except IntelligenceError:
            raise IntelligenceError("TOOL_NOT_ALLOWLISTED") from None
        refs = r.get("evidence_refs")
        need(type(refs) is list and refs, "NO_EVIDENCE_REFS")
        return entry, cutoff, calls, deadline, tools, context, refs

    def _rejected(self, r: dict, reason: str, now: int) -> Document:
        keep = {k: r.get(k) for k in ("job_id", "run_id", "issuer_id", "context_hash", "policy_profile_hash",
                                      "cutoff_ms") if type(r.get(k)) in (str, int)}
        result = {"schema": RESULT_SCHEMA, **keep, "status": "REJECTED_REQUEST",
                  "reasons": [reason], "model_hash": self.model.identity.model_hash,
                  "prompt_hash": self.config.prompt_sha256, "claims": [], "novelty": {}, "conflicts": [],
                  "missingness": [reason], "confidence": {"level": "UNKNOWN", "calibrated": False},
                  "falsifiers": [], "expiry_ms": now + 1, "review_requests": [], "proposed_thesis": None,
                  "rationale": f"Request rejected before assessment: {reason}.",
                  "model_io": {"steps": [], "tool_calls": [], "note": "no model call"},
                  "started_ms": now, "completed_ms": now}
        result["result_id"] = "res:" + digest("larp.intel.result.v1", result)
        return Document.from_dict(result)

    # ------------------------------------------------------------------ assess
    def assess(self, request: Document) -> Document:
        start = self.clock()
        r = request.read()
        try:
            validated = self._validate(r)
        except (IntelligenceError, KeyError, TypeError) as exc:
            return self._rejected(r, str(exc) if isinstance(exc, IntelligenceError) else "MALFORMED", start)
        box, cancel = {}, threading.Event()

        def work():
            try:
                box["result"] = self._assess(r, start, validated, cancel)
            except BaseException as exc:  # re-raised in the caller's thread
                box["error"] = exc

        worker = threading.Thread(target=work, name=f"larp-assess:{r['job_id']}", daemon=True)
        worker.start()
        worker.join(validated[3] / 1000)  # wall-clock hard stop at the request deadline
        if worker.is_alive():
            cancel.set()  # no further model or tool call; whatever the worker returns is discarded
            return self._abandoned(r, validated, start)
        if "error" in box:
            raise box["error"]
        return box["result"]

    def _assess(self, r, start, validated, cancel) -> Document:
        entry, cutoff, max_calls, deadline, tools, context, refs = validated
        index = EvidenceIndex(self.reader, entry, cutoff)
        state = _State(entry, index, self.config, cutoff, tools, context)
        self._load_refs(state, refs)
        self._source_health(state, r.get("source_health"))
        status, reasons, model_io, claims_out, rejected = None, [], [], None, []
        if not state.current_records:
            status, reasons = "UNAVAILABLE", ["NO_USABLE_EVIDENCE"]
        step = 0
        while status is None:
            if cancel.is_set():
                status, reasons = "UNAVAILABLE", ["ASSESSMENT_DEADLINE_EXCEEDED"]
                break
            remaining = deadline - (self.clock() - start)
            if remaining <= 0:
                status, reasons = "UNAVAILABLE", ["TIME_BUDGET_EXHAUSTED"]
                break
            gaps = state.gaps()
            calls_left = max_calls - len(state.tool_calls)
            m_request = {"schema": "ModelRequest.v1", "request_id": f"{r['job_id']}:step:{step}",
                         "model": self.model.identity.record(), "prompt_sha256": self.config.prompt_sha256,
                         "input": state.view(gaps, calls_left)}
            step += 1
            try:
                m_response = self.model.step(Document.from_dict(m_request), remaining).read()
            except Exception as exc:  # adapter defect: unavailable, never a silent success
                model_io.append({"request_id": m_request["request_id"], "error": type(exc).__name__})
                status, reasons = "UNAVAILABLE", ["MODEL_ERROR"]
                break
            model_io.append({"request": m_request, "response": m_response})
            if m_response["status"] == "TIMEOUT" or self.clock() - start > deadline:
                status, reasons = "UNAVAILABLE", ["MODEL_TIMEOUT"]
                break
            if m_response["status"] == "ERROR":
                status, reasons = "UNAVAILABLE", ["MODEL_ERROR"]
                break
            if m_response["status"] != "OK":
                status, reasons = "ABSTAIN", ["MODEL_OUTPUT_INVALID"]
                break
            try:
                action = parse_output(m_response["output"])
            except IntelligenceError as exc:
                status, reasons = "ABSTAIN", [str(exc)]
                break
            if action["action"] == "FINISH":
                claims_out = action.get("claims", [])
                break
            if calls_left <= 0:
                state.missing.append("TOOL_BUDGET_EXHAUSTED")
                claims_out = None  # harness facts only; the model did not confirm
                break
            if cancel.is_set():
                continue  # the loop head records the abandonment
            self._call_tool(state, action["tool"], action["args"])
        return self._result(r, state, entry, start, status, reasons, model_io, claims_out, rejected)

    def _load_refs(self, state, refs):
        seen_records, seen_content = set(), set()
        for ref in refs:
            if type(ref) is not dict or type(ref.get("record_id")) is not str:
                state.missing.append("EVIDENCE_REF_MALFORMED")
                continue
            if type(ref.get("available_ms")) is not int or ref["available_ms"] > state.cutoff:
                state.missing.append(f"FUTURE_EVIDENCE_REF:{ref['record_id']}")
                continue
            record = state.index.all_by_id.get(ref["record_id"])
            if record is None:
                state.missing.append(f"EVIDENCE_NOT_AVAILABLE_AT_CUTOFF:{ref['record_id']}")
                continue
            if ref.get("content_hash") not in (None, record["content_hash"]):
                state.missing.append(f"EVIDENCE_HASH_MISMATCH:{record['accession']}")
                continue
            latest = state.index.by_accession[record["accession"]]
            if latest["record_id"] != record["record_id"]:
                state.missing.append(f"REVISION_SUPERSEDED_REF:{record['accession']}")
                record = latest
            if record["record_id"] in seen_records or record["content_hash"] in seen_content:
                continue  # repeated evidence counts once
            if record["quality"] == "MISSING":
                state.missing.append(f"FILING_UNREADABLE:{record['accession']}")
                continue
            seen_records.add(record["record_id"]), seen_content.add(record["content_hash"])
            state.current_records.append(record["record_id"])
            if record.get("incomplete"):
                state.missing.append(f"FILING_INCOMPLETE:{record['accession']}")
            load_items(state, record)
            for doc in record["documents"]:
                if doc["role"] == "PRIMARY":
                    try:
                        load_document(state, record, doc)
                    except ToolError as exc:
                        state.missing.append(f"PRIMARY_UNREADABLE:{record['accession']}:{exc}")

    def _source_health(self, state, health):
        if type(health) is not dict:
            state.missing.append("SOURCE_HEALTH_UNKNOWN")
            return
        last = health.get("last_success_ms")
        if health.get("status") != "OK" or type(last) is not int or \
                state.cutoff - last > self.config.p("max_source_staleness_ms"):
            state.missing.append("SOURCE_STALE")

    def _call_tool(self, state, tool, args):
        started = self.clock()
        key = (tool, Document.from_dict(args).payload) if type(args) is dict else (tool, b"")
        state.attempted.add(key)
        record = {"index": len(state.tool_calls), "tool": tool, "args": args if type(args) is dict else {},
                  "started_ms": started}
        try:
            result = run_tool(state, tool, args)
            record.update(status=result.get("status", "OK"), error=None,
                          result_sha256=Document.from_dict({"r": result}).digest("larp.intel.tool.v1"))
            summary = {k: v for k, v in result.items() if k != "excerpt"}
            state.tool_results.append(dict(summary, tool=tool, excerpt=result.get("excerpt")))
        except ToolError as exc:
            record.update(status="TOOL_ERROR", error=str(exc), result_sha256=None)
            state.tool_results.append({"tool": tool, "status": "TOOL_ERROR", "error": str(exc)})
            state.missing.append(f"TOOL_ERROR:{tool}:{exc}")
        record["latency_ms"] = self.clock() - started
        state.tool_calls.append(record)

    # ------------------------------------------------------------------ result
    def _verify_claims(self, state, claims):
        verified, rejected = [], []
        records = state.index.all_by_id
        for i, claim in enumerate(claims if type(claims) is list else []):
            if i >= self.config.limits["max_claims"]:
                rejected.append({"index": i, "reason": "TOO_MANY_CLAIMS"})
                continue
            try:
                fact, reason = verify_claim(self._bind_source(state, claim), state.texts, records,
                                            issuer_names=issuer_names(state.entry))
            except Exception as exc:  # anything the schema check missed is a rejected claim, never a crash
                fact, reason = None, f"CLAIM_MALFORMED:{type(exc).__name__}"
            if fact is None:
                rejected.append({"index": i, "reason": reason, "metric": claim.get("metric") if type(claim) is dict else None})
                continue
            if fact["source"].get("accession") not in state.current_accessions:
                rejected.append({"index": i, "reason": "CLAIM_NOT_FROM_ASSESSED_FILING"})
                continue
            state.facts.setdefault(fact["fact_id"], fact)
            verified.append(fact["fact_id"])
        return verified, rejected

    def _bind_source(self, state, claim):
        """A claim naming no source record is attributed to the record holding its cited document.

        A named record is kept: the verifier then requires that record to hold the cited
        document and takes all provenance from it, so a span from an earlier filing can never
        be presented as evidence from the assessed one.
        """
        if type(claim) is not dict or not (claim.get("source") is None or type(claim["source"]) is dict):
            return claim  # malformed: the verifier rejects it
        if (claim.get("source") or {}).get("record_id") is not None:
            return claim
        return dict(claim, source=self._source_for(state, claim))

    def _source_for(self, state, claim):
        span = claim.get("span") if type(claim.get("span")) is dict else {}
        others = [x for x in state.index.all_by_id if x not in state.current_records]
        for record_id in list(state.current_records) + others:
            record = state.index.all_by_id[record_id]
            for doc in record["documents"]:
                if doc["text_sha256"] and doc["text_sha256"] == span.get("doc"):
                    return {"record_id": record_id, "accession": record["accession"], "doc_name": doc["name"],
                            "available_ms": record["available_ms"], "original_ms": record["original_ms"]}
        return {"record_id": None, "accession": None, "doc_name": None, "available_ms": None, "original_ms": None}

    def _result(self, r, state, entry, start, status, reasons, model_io, claims_out, rejected):
        config = self.config
        confirmed = set()
        if status is None and claims_out is not None:
            confirmed, rejected = self._verify_claims(state, claims_out)
            if rejected:
                status, reasons = "ABSTAIN", ["UNSUPPORTED_CLAIM"]
        current, unverified = self._reverify_harness_events(state, state.current_facts())
        priors = state.prior_facts()
        conflicts = detect_conflicts(current + [f for f in priors if f["kind"] == "REPORTED"]) if current else []
        conflicts = [c for c in conflicts if set(c["fact_ids"]) & {f["fact_id"] for f in current}]
        if status is None and conflicts:
            status, reasons = "ABSTAIN", ["CONFLICTING_EVIDENCE"]
        status = status or "ASSESSED"
        unread = state.unread_exhibits()
        for accession, name in unread:
            state.missing.append(f"EXHIBIT_NOT_LOADED:{accession}:{name}")
        novelty = self._novelty(state, current, priors)
        for fact in current:  # no earlier comparison point: recorded as missing, never invented
            if novelty["by_fact"][fact["fact_id"]] == "NO_PRIOR_AVAILABLE":
                state.missing.append(f"PRIOR_MISSING:{fact['metric']}:{fact['kind']}:{fact['period']}")
        for metric in unverified:
            state.missing.append(f"EVIDENCE_HARNESS_FACT_UNVERIFIED:{metric}")
        statements = [self._statement_record(state, f, novelty) for f in current if is_statement(f["metric"])]
        coverage = dict(state.coverage, documents_truncated=sorted(state.coverage["documents_truncated"]))
        coverage["complete"] = not (coverage["documents_truncated"] or coverage["facts_truncated"]
                                    or coverage["statements_truncated"] or coverage["prior_records_truncated"]
                                    or coverage["statement_comparisons_truncated"] or coverage["model_input_truncated"]
                                    or state.unread_exhibits())
        if not coverage["complete"]:
            state.missing.append("COVERAGE_TRUNCATED")
        findings = self._findings(state, current)
        thesis, falsifiers = self._thesis(r, state, current, findings, status, bool(unread))
        missing = sorted(set(state.missing))
        if state.injection:
            missing.append("UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE")
        now = self.clock()
        records = [state.index.all_by_id[x] for x in state.current_records]
        coverage["prior_history"] = {m: state.history_complete.get(m, False) for m in sorted(state.queried_prior)}
        freshness = {"cutoff_ms": state.cutoff,
                     "newest_available_ms": max((x["available_ms"] for x in records), default=None),
                     "newest_original_ms": max((x["original_ms"] for x in records), default=None),
                     "source_stale": "SOURCE_STALE" in missing or "SOURCE_HEALTH_UNKNOWN" in missing}
        freshness["evidence_age_ms"] = (None if freshness["newest_available_ms"] is None
                                        else state.cutoff - freshness["newest_available_ms"])
        impact, severity = _overall(findings)
        confidence = self._confidence(status, missing, novelty, current)
        key = digest("larp.intel.assessment-key.v1", {
            "issuer_id": entry.issuer_id, "cutoff_ms": state.cutoff,
            "content": sorted(x["content_hash"] for x in records), "context_hash": r["context_hash"],
            "policy_profile_hash": r["policy_profile_hash"], "model_hash": self.model.identity.model_hash,
            "prompt_sha256": config.prompt_sha256, "config_sha256": config.config_sha256,
            "tools": list(state.allowed_tools), "budget": r["budget"]})
        ids = {s["fact_id"]: s["statement_id"] for s in statements}
        claims = [self._claim(f, novelty, confirmed, ids) for f in current] if status == "ASSESSED" else []
        # Supported facts are kept for audit and reassessment when the result is not ASSESSED. Retention never
        # changes the status, clears the gate, permits entry or widens any exit authority (IDEA-031 S2.3).
        retained = [self._claim(f, novelty, confirmed, ids) for f in current] if status != "ASSESSED" else []
        reviews = self._reviews(r, entry, status, reasons, missing, key, now,
                                new_statement=any(lifecycle.needs_review(s["novelty"]) for s in statements))
        steps_cost = [s["response"]["cost"] for s in model_io if "response" in s]
        result = {
            "schema": RESULT_SCHEMA, "job_id": r["job_id"], "run_id": r["run_id"], "issuer_id": entry.issuer_id,
            "context_hash": r["context_hash"], "policy_profile_hash": r["policy_profile_hash"],
            "cutoff_ms": state.cutoff, "assessment_key": key, "status": status, "reasons": reasons,
            "model": self.model.identity.record(), "model_hash": self.model.identity.model_hash,
            "prompt_hash": config.prompt_sha256, "config_sha256": config.config_sha256,
            "instrument_scope": {"issuer_id": entry.issuer_id, "token": entry.token,
                                 "token_underlying_status": entry.token_underlying_status,
                                 "note": "issuer-level evidence; not converted to any listing or token"},
            "evidence_used": [{"record_id": x["record_id"], "accession": x["accession"], "form": x["form"],
                               "content_hash": x["content_hash"], "available_ms": x["available_ms"],
                               "original_ms": x["original_ms"], "revision": x["revision"],
                               "supersedes": x["supersedes"], "quality": x["quality"]} for x in records],
            "claims": claims, "retained_facts": retained, "rejected_claims": rejected, "novelty": novelty["summary"],
            "conflicts": conflicts, "findings": findings if status == "ASSESSED" else [],
            # Filer item codes and keyword events verified by the harness stand even when the
            # model abstains or times out; numerical findings need an ASSESSED result.
            "event_findings": [f for f in findings if "metric" not in f],
            # Statements about events that are not the issuer's current occurrence (announced, reported, forecast,
            # conditional, third-party, historical), verified with their semantics. Never findings; first-seen or
            # changed ones are sent for bounded review by the evidence state (gate.py / lifecycle.py).
            "event_statements": statements, "coverage": coverage,
            "impact": impact if status == "ASSESSED" else "UNKNOWN",
            "severity": severity if status == "ASSESSED" else None,
            "missingness": missing, "confidence": confidence, "freshness": freshness,
            "falsifiers": falsifiers, "proposed_thesis": thesis if status == "ASSESSED" else None,
            "expiry_ms": now + config.p("result_ttl_ms"), "review_requests": reviews,
            "budget_used": {"tool_calls": len(state.tool_calls), "model_steps": len(model_io),
                            "elapsed_ms": now - start},
            "cost": {"amount_micro_usd": (sum(c["amount_micro_usd"] for c in steps_cost)
                                          if all(c["amount_micro_usd"] is not None for c in steps_cost) else None),
                     "basis": sorted({c["basis"] for c in steps_cost})},
            "model_io": {"steps": model_io, "tool_calls": state.tool_calls,
                         "cot": [s["response"]["reasoning_summary"] for s in model_io
                                 if "response" in s and s["response"]["reasoning_summary"]]},
            "started_ms": start, "completed_ms": now,
        }
        result["rationale"] = _rationale(result, entry)
        assert_no_trade_fields({k: v for k, v in result.items() if k != "model_io"}, "AssessmentResult")
        result["result_id"] = "res:" + digest("larp.intel.result.v1", result)
        return Document.from_dict(result)

    def _abandoned(self, r, validated, start) -> Document:
        """UNAVAILABLE at the hard deadline. Nothing from the abandoned worker is read or used."""
        entry, cutoff, _, _, tools, _, refs = validated
        now, reasons = self.clock(), ["ASSESSMENT_DEADLINE_EXCEEDED"]
        key = digest("larp.intel.assessment-key.v1", {
            "issuer_id": entry.issuer_id, "cutoff_ms": cutoff, "evidence_refs": refs, "context_hash": r["context_hash"],
            "policy_profile_hash": r["policy_profile_hash"], "model_hash": self.model.identity.model_hash,
            "prompt_sha256": self.config.prompt_sha256, "config_sha256": self.config.config_sha256,
            "tools": list(tools), "budget": r["budget"], "outcome": "DEADLINE_EXCEEDED"})
        result = {
            "schema": RESULT_SCHEMA, "job_id": r["job_id"], "run_id": r["run_id"], "issuer_id": entry.issuer_id,
            "context_hash": r["context_hash"], "policy_profile_hash": r["policy_profile_hash"], "cutoff_ms": cutoff,
            "assessment_key": key, "status": "UNAVAILABLE", "reasons": reasons,
            "model": self.model.identity.record(), "model_hash": self.model.identity.model_hash,
            "prompt_hash": self.config.prompt_sha256, "config_sha256": self.config.config_sha256,
            "evidence_used": [], "claims": [], "retained_facts": [], "rejected_claims": [], "novelty": {},
            "conflicts": [], "findings": [], "event_findings": [], "event_statements": [],
            "coverage": {"complete": False, "note": "abandoned at the deadline"}, "impact": "UNKNOWN", "severity": None,
            "missingness": reasons,
            "confidence": {"level": "UNKNOWN", "calibrated": False, "basis": "status UNAVAILABLE"},
            "freshness": None, "falsifiers": [], "proposed_thesis": None,
            "expiry_ms": now + self.config.p("result_ttl_ms"),
            "review_requests": self._reviews(r, entry, "UNAVAILABLE", reasons, reasons, key, now),
            "budget_used": {"tool_calls": None, "model_steps": None, "elapsed_ms": now - start},
            "cost": {"amount_micro_usd": None, "basis": ["UNKNOWN_ABANDONED_AT_DEADLINE"]},
            "model_io": {"steps": [], "tool_calls": [],
                         "note": "worker abandoned at the deadline; its records are not part of this result"},
            "started_ms": start, "completed_ms": now,
        }
        result["rationale"] = _rationale(result, entry)
        assert_no_trade_fields({k: v for k, v in result.items() if k != "model_io"}, "AssessmentResult")
        result["result_id"] = "res:" + digest("larp.intel.result.v1", result)
        return Document.from_dict(result)

    def _novelty(self, state, current, priors):
        by_fact, counts = {}, {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0, "NO_PRIOR_AVAILABLE": 0,
                               "PRIOR_NOT_CHECKED": 0, "REPEATED": 0, "FIRST_SEEN": 0, "HISTORY_UNAVAILABLE": 0,
                               "UNCERTAIN_MATCH": 0, "ALREADY_SEEN": 0}
        state.statement_ids, state.statement_matches = {}, {}
        known_events = {(f["metric"], f["source"].get("accession")) for f in state.context_facts if f["kind"] == "EVENT"}
        # Statements already accepted into this issuer's context (any filing, including a reread of this one) and
        # statements in earlier filings; both bounded by max_statement_comparisons.
        seen = [self._signed(state, f) for f in state.context_facts if is_statement(f["metric"])]
        earlier = [self._signed(state, p) for p in priors if is_statement(p["metric"])]
        cap = state.config.limits["max_statement_comparisons"]
        for fact in current:
            if is_statement(fact["metric"]):
                sig = self._signed(state, fact)
                again = lifecycle.novelty(sig["fingerprint"], seen, checked=True, history_complete=True,
                                          max_comparisons=cap)
                state.coverage["statement_comparisons"] += again["compared"]
                if again["label"] == "REPEATED":
                    label, match = "ALREADY_SEEN", again["match"]
                else:
                    found = lifecycle.novelty(sig["fingerprint"], earlier, checked=STATEMENTS in state.queried_prior,
                                              history_complete=state.history_complete.get(STATEMENTS, False),
                                              max_comparisons=cap)
                    state.coverage["statement_comparisons"] += found["compared"]
                    if found["truncated"] or again["truncated"]:
                        state.coverage["statement_comparisons_truncated"] += 1
                    label, match = found["label"], found["match"]
                reuse = match and match["relation"] in ("EXACT", "SEMANTIC_SAME")
                state.statement_ids[fact["fact_id"]] = (match["prior_id"] if reuse else
                                                        lifecycle.statement_id(sig["fingerprint"]))
                state.statement_matches[fact["fact_id"]] = match
            elif fact["kind"] == "EVENT":
                label = "REPEATED" if (fact["metric"], fact["source"].get("accession")) in known_events else "NEW"
            elif not fact["period"]:
                label = "PRIOR_NOT_CHECKED"
            else:
                same = [p for p in priors if (p["metric"], p["period"], p["unit"], p["security_scope"]) ==
                        (fact["metric"], fact["period"], fact["unit"], fact["security_scope"])]
                if not same and fact["metric"] not in state.queried_prior:
                    label = "PRIOR_NOT_CHECKED"
                elif not same:
                    label = "NO_PRIOR_AVAILABLE"
                else:
                    same_kind = [p for p in same if p["kind"] == fact["kind"]]
                    label = ("NEW" if not same_kind else
                             "UNCHANGED" if all(values_agree(fact, p) for p in same_kind) else "CHANGED")
            by_fact[fact["fact_id"]] = label
            counts[label] += 1
        return {"by_fact": by_fact, "summary": {k.lower(): v for k, v in counts.items()}}

    @staticmethod
    def _signed(state, fact) -> dict:
        """{"id", "signature"} of a statement fact: its recorded statement_id if it has one, else a new one."""
        sig = lifecycle.signature(statement_event(fact["metric"]), fact.get("statement"), fact["span"]["text"])
        return {"id": fact.get("statement_id") or lifecycle.statement_id(sig), "fingerprint": sig}

    def _statement_record(self, state, fact, novelty) -> dict:
        sem = fact.get("statement") or {}
        record = state.index.all_by_id.get(fact["source"].get("record_id")) or {}
        return {"type": fact["metric"], "event": statement_event(fact["metric"]), "fact_id": fact["fact_id"],
                "statement_id": state.statement_ids[fact["fact_id"]], "novelty": novelty["by_fact"][fact["fact_id"]],
                "match": state.statement_matches.get(fact["fact_id"]), "statement": fact["span"]["text"],
                "semantics": sem or None, "fingerprint": self._signed(state, fact)["fingerprint"],
                "accession": fact["source"].get("accession"), "record_id": fact["source"].get("record_id"),
                "content_hash": record.get("content_hash")}

    @staticmethod
    def _claim(fact, novelty, confirmed, statement_ids) -> dict:
        claim = dict(fact, novelty=novelty["by_fact"].get(fact["fact_id"]), model_confirmed=fact["fact_id"] in confirmed)
        if fact["fact_id"] in statement_ids:
            claim["statement_id"] = statement_ids[fact["fact_id"]]
        return claim

    def _reverify_harness_events(self, state, current) -> tuple:
        """Keyword event facts are re-verified against their source text before they can support anything; a fact
        that fails (or an event fact without recorded semantics) is dropped from this result, so an unsupported
        deterministic finding cannot survive verification or a model abstention (IDEA-031 AC-S11)."""
        records, names, kept, failed = state.index.all_by_id, issuer_names(state.entry), [], []
        for fact in current:
            if fact["kind"] != "EVENT" or fact["metric"].startswith("ITEM:"):
                kept.append(fact)
                continue
            verified, reason = verify_claim(fact_as_claim(fact), state.texts, records, issuer_names=names)
            if verified is None or verified["fact_id"] != fact["fact_id"]:
                failed.append(fact["metric"])
                state.facts.pop(fact["fact_id"], None)
                continue
            kept.append(fact)
        return kept, sorted(set(failed))

    def _findings(self, state, current):
        severity = self.config.severity
        findings = []
        for fact in current:
            if fact["kind"] != "EVENT" or is_statement(fact["metric"]):
                continue  # a statement about an event is never a finding (event_statements, review)
            if fact["metric"].startswith("ITEM:"):
                rule = severity["items"].get(fact["metric"][5:])
            elif fact.get("statement") is not None and finding_eligible(fact["statement"]):
                rule = severity["keywords"].get(fact["metric"])
            else:
                rule = None  # legacy event fact without recorded semantics: kept, never a finding
            if rule:
                findings.append({"type": fact["metric"], "impact": rule[0], "severity": rule[1],
                                 "fact_ids": [fact["fact_id"]],
                                 "sources": [{"accession": fact["source"].get("accession"),
                                              "record_id": fact["source"].get("record_id")}]})
        labels = {("GUIDANCE", "LOWER"): "GUIDANCE_LOWERED", ("GUIDANCE", "HIGHER"): "GUIDANCE_RAISED",
                  ("REPORTED_VS_PRIOR_GUIDANCE", "BELOW"): "REPORTED_BELOW_PRIOR_GUIDANCE",
                  ("REPORTED_VS_PRIOR_GUIDANCE", "ABOVE"): "REPORTED_ABOVE_PRIOR_GUIDANCE",
                  ("REPORTED_VS_PRIOR_GUIDANCE", "WITHIN"): "REPORTED_WITHIN_PRIOR_GUIDANCE"}
        current_ids = {f["fact_id"] for f in current}
        for (new_id, prior_id), comparison in sorted(state.comparisons.items()):
            if new_id not in current_ids or comparison["relation"] == "INCOMPARABLE" or \
                    not comparison.get("applicable", True):
                continue  # superseded or conflicting prior guidance stays audit-only
            basis = comparison.get("basis", "")
            group = "GUIDANCE" if basis == "GUIDANCE_VS_PRIOR_GUIDANCE" else basis
            label = labels.get((group, comparison["relation"]))
            if label:
                rule = severity["comparisons"][label]
                findings.append({"type": label, "impact": rule[0], "severity": rule[1],
                                 "metric": state.facts[new_id]["metric"], "period": state.facts[new_id]["period"],
                                 "fact_ids": [new_id, prior_id], "delta": comparison.get("delta")})
        unique, seen = [], set()
        for finding in findings:
            key = (finding["type"], finding.get("metric"), finding.get("period"))
            if key in seen:
                continue
            seen.add(key)
            finding["finding_id"] = "find:" + digest("larp.intel.finding.v1", finding)
            unique.append(finding)
        return sorted(unique, key=lambda f: f["finding_id"])

    def _thesis(self, r, state, current, findings, status, unread):
        prior = (r.get("context") or EMPTY_CONTEXT)["thesis"]
        definitions = list(prior["falsifiers"]) if prior else [dict(f) for f in self.config.default_falsifiers]
        is_8k = any(state.index.all_by_id[x]["form"].startswith("8-K") for x in state.current_records)
        types = {f["type"] for f in findings}
        states = []
        for f in definitions:
            kind, fired, basis = f["type"], "UNKNOWN", []
            if kind == "ITEM":
                hit = [x["fact_id"] for x in current if x["metric"] == f"ITEM:{f['item']}"]
                fired = "FIRED" if hit else ("NOT_FIRED" if is_8k else "NOT_APPLICABLE")
                basis = hit
            elif kind == "EVENT":
                hit = [x["fact_id"] for x in current if x["metric"] == f["event"]]
                fired = "FIRED" if hit else ("UNKNOWN" if unread else "NOT_FIRED")
                basis = hit
            elif kind in ("GUIDANCE_LOWERED", "REPORTED_BELOW_PRIOR_GUIDANCE"):
                relevant = [x for x in findings if x.get("metric") == f["metric"]]
                hit = [x for x in relevant if x["type"] == kind]
                kinds = {"GUIDANCE_LOWERED": "GUIDANCE", "REPORTED_BELOW_PRIOR_GUIDANCE": "REPORTED"}
                has_fact = any(x["kind"] == kinds[kind] and x["metric"] == f["metric"] for x in current)
                compared = [c for (n, _), c in state.comparisons.items()
                            if state.facts[n]["metric"] == f["metric"] and state.facts[n]["kind"] == kinds[kind]
                            and c["relation"] != "INCOMPARABLE" and c.get("applicable", True)]
                fired = ("FIRED" if hit else ("UNKNOWN" if unread else "NOT_APPLICABLE") if not has_fact else
                         "NOT_FIRED" if compared else "UNKNOWN")
                basis = [i for x in hit for i in x["fact_ids"]]
            states.append({"falsifier_id": f["falsifier_id"], "type": kind, "state": fired, "fact_ids": basis})
        if status != "ASSESSED":
            return None, states
        adverse = any(x["impact"] == "ADVERSE" for x in findings)
        fired = [s["falsifier_id"] for s in states if s["state"] == "FIRED"]
        unknown = any(s["state"] == "UNKNOWN" for s in states)
        new_status = ("BROKEN" if fired else "WEAKENED" if adverse else
                      "UNKNOWN" if unknown or not current else "INTACT")
        version = (prior["version"] + 1) if prior else 1
        thesis = {"thesis_id": prior["thesis_id"] if prior else f"thesis:{state.entry.issuer_id}",
                  "version": version, "previous_version": prior["version"] if prior else None,
                  "previous_status": prior["status"] if prior else None, "status": new_status,
                  "based_on_context_hash": r["context_hash"], "falsifiers": definitions,
                  "fired_falsifiers": fired, "finding_ids": [x["finding_id"] for x in findings],
                  "supporting_fact_ids": [x["fact_id"] for x in current],
                  "revised": (prior is None) or new_status != prior["status"] or bool(findings)}
        return thesis, states

    def _confidence(self, status, missing, novelty, current):
        if status != "ASSESSED":
            return {"level": "UNKNOWN", "calibrated": False, "basis": f"status {status}"}
        if not current:
            level = "UNKNOWN"
        elif missing:
            level = "LOW"
        elif novelty["summary"]["no_prior_available"] or novelty["summary"]["prior_not_checked"]:
            level = "MEDIUM"
        else:
            level = "HIGH"
        return {"level": level, "calibrated": False,
                "basis": "ordinal rule over verified-fact count, missingness and comparison coverage; not a probability"}

    def _reviews(self, r, entry, status, reasons, missing, key, now, new_statement=False):
        config, wanted = self.config, []
        if status == "UNAVAILABLE":
            wanted.append(("RETRY_AFTER_UNAVAILABLE", config.p("retry_delay_ms")))
        if "CONFLICTING_EVIDENCE" in reasons or any(m.startswith("PRIOR_GUIDANCE_CONFLICT:") for m in missing):
            wanted.append(("CONFLICT_RESOLUTION", config.p("reassess_delay_ms")))
        if "UNSUPPORTED_CLAIM" in reasons or "MODEL_OUTPUT_INVALID" in reasons or \
                any(x.startswith("MODEL_OUTPUT_") for x in reasons):
            wanted.append(("REASSESS_AFTER_ABSTENTION", config.p("retry_delay_ms")))
        if any(m.startswith("PRIOR_MISSING:") for m in missing):
            wanted.append(("AWAIT_COMPARISON_BASIS", config.p("reassess_delay_ms")))
        if "SOURCE_STALE" in missing or "SOURCE_HEALTH_UNKNOWN" in missing:
            wanted.append(("RETRY_AFTER_SOURCE_RECOVERY", config.p("retry_delay_ms")))
        if any(m.startswith(("TOOL_ERROR:", "EXHIBIT_NOT_LOADED:", "TOOL_BUDGET")) for m in missing):
            wanted.append(("COMPLETE_EVIDENCE", config.p("retry_delay_ms")))
        if new_statement:  # the evidence state decides whether a review is still needed (bounded, lifecycle.py)
            wanted.append(("REVIEW_NEW_STATEMENT", config.p("reassess_delay_ms")))
        out = []
        for reason, delay in wanted:
            payload = {"kind": "REASSESS_ISSUER", "issuer_id": entry.issuer_id, "reason": reason,
                       "after_assessment_key": key}
            job_id = "evidence:" + digest("larp.intel.review.v1", payload)
            out.append({"request_id": job_id, "kind": "REASSESS", "reason": reason, "due_ms": now + delay,
                        "job": {"job_id": job_id, "lane": "evidence", "due_ms": now + delay,
                                "valid_until_ms": now + delay + config.p("job_validity_ms"),
                                "max_attempts": config.p("job_max_attempts"), "priority": 40,
                                "calendar_id": "UTC", "tzdata_version": "utc-only-no-tzdata",
                                "missed": "catch_up", "payload": payload}})
        return out


def _overall(findings):
    impacts = {f["impact"] for f in findings} - {"UNKNOWN"}
    severity = max((f["severity"] for f in findings), default=0)
    if "ADVERSE" in impacts and "FAVOURABLE" in impacts:
        return "MIXED", severity
    for label in ("ADVERSE", "FAVOURABLE", "IMMATERIAL"):
        if label in impacts:
            return label, severity
    return ("UNKNOWN" if not findings else "IMMATERIAL"), severity


def _rationale(result, entry):
    """At most three sentences, generated only from verified structured fields (G-04)."""
    forms = ", ".join(sorted({f"{e['form']} {e['accession']}" for e in result["evidence_used"]})) or "no filing"
    if result["status"] != "ASSESSED":
        return (f"{entry.entity_name} ({forms}): {result['status'].lower()} because "
                f"{', '.join(result['reasons']).lower().replace('_', ' ')}. No thesis update; "
                f"{len(result['review_requests'])} reassessment request(s) recorded.")
    numeric = [c for c in result["claims"] if c["kind"] != "EVENT"]
    parts = [f"{entry.entity_name} ({forms}): {len(numeric)} verified numerical fact(s)"]
    findings = [f for f in result["findings"] if f["type"].startswith(("GUIDANCE", "REPORTED"))]
    if findings:
        parts[0] += "; " + "; ".join(f"{f['metric']} {f['period']} {f['type'].lower().replace('_', ' ')}"
                                     for f in findings[:3])
    events = [f["type"] for f in result["findings"] if not f["type"].startswith(("GUIDANCE", "REPORTED"))]
    if events:
        parts[0] += f"; events {', '.join(events[:4])}"
    missing = [m for m in result["missingness"] if m.startswith("PRIOR_MISSING")]
    second = (f"No earlier comparison point was available for {', '.join(m.split(':', 1)[1] for m in missing[:3])}"
              if missing else "Comparison points were found for every checked fact" if numeric else
              "No numerical fact was found")
    thesis = result["proposed_thesis"]
    third = (f"Proposed thesis {thesis['status']} (v{thesis['version']}); falsifiers fired: "
             f"{', '.join(thesis['fired_falsifiers']) or 'none'}; confidence {result['confidence']['level']} (uncalibrated)")
    return f"{parts[0]}. {second}. {third}."


def build_request(*, job: dict, run_id: str, issuer_id: str, records: list, cutoff_ms: int, context: dict,
                  policy_profile_hash: str, allowed_tools: list, tool_calls: int, deadline_ms: int,
                  source_health: dict | None) -> Document:
    """AssessmentRequest.v1 from an ingestion job and the records it references."""
    refs = [{"record_id": x["record_id"], "accession": x["accession"], "source": x["source_id"],
             "quality": x["quality"], "observed_ms": x["retrieved_ms"], "available_ms": x["available_ms"],
             "content_hash": x["content_hash"]} for x in records]
    return Document.from_dict({
        "schema": "AssessmentRequest.v1", "job_id": job["job_id"], "run_id": run_id, "issuer_id": issuer_id,
        "cutoff_ms": cutoff_ms, "evidence_refs": refs, "context": context, "context_hash": context_hash(context),
        "policy_profile_hash": policy_profile_hash, "allowed_tools": allowed_tools,
        "budget": {"tool_calls": tool_calls, "deadline_ms": deadline_ms}, "source_health": source_health})
