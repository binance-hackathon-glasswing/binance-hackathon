# IDEA-030 V01: evidence semantic probes

Prospective expectations recorded before execution, 2026-10-10. Imports use unchanged already-pushed evidence code at `544df90`; review criteria are committed at `703a10a`. Inline, read-only function calls and deterministic synthetic helpers only; no source/test files added, no network, hosted/local model, wallet or trading calls.

1. Input `Impairment of goodwill`. Correct semantic behavior: a heading/noun phrase alone must not establish an occurred impairment or an adverse event.
2. Input `Our competitor reported a cybersecurity incident.` Correct semantic behavior: preserve third-party attribution; it must not establish that the filing issuer suffered the incident.
3. Input `The CEO is rumored to resign.` Correct semantic behavior: distinguish the existence of a rumor from an asserted resignation/confirmed announcement.
4. Input `The CEO announced plans to resign effective November 30.` Correct semantic behavior: an asserted announcement now with a future effective departure; preserve announcement certainty independently of future occurrence. A classification called HYPOTHETICAL may retain text, but cannot by itself represent both dimensions.
5. Input `Revenue for the third quarter of fiscal 2027 was $35.1 billion.` Correct behavior: a claim keeping the exact source span while changing value to -35.1, or kind to GUIDANCE, must fail semantic verification. Unchanged claim must pass. Probe verifier outputs separately from aggregate conflict/assessment defenses.
6. Reassess the same synthetic `HYPOTHETICAL_BOILERPLATE` filing after accepting its first result and advancing six hours, with fresh source health and updated context. Expected safety/property distinction: preserve initially new statement, but provide an acknowledgment or bounded review lifecycle; it must not imply new information arrived at each rereview. Record novelty, gate and requested rereview to identify whether such a lifecycle exists.
7. Produce and accept a CLEAR result on existing synthetic `EXSEMI_502_8K`; produce a second valid result with updated context, advance beyond its expiry, then attempt acceptance. Correct incoming-result behavior: REJECT_EXPIRED. Consumption safety requirement: previously stored CLEAR must not authorize actions after its own validity window; record whether reducer stores/ages that state. This probes a component boundary, not actual live policy behavior.

All inputs are constructed synthetic sentences; this is not an estimate of real-filing error frequency.

## Observed output

Executed using Python 3.12.14. No network or external model calls.

```json
[
  {
    "case": "heading",
    "input": "Impairment of goodwill",
    "facts": [
      {
        "metric": "IMPAIRMENT",
        "kind": "EVENT",
        "period": null,
        "scope": "ISSUER",
        "span": "Impairment",
        "verification_reason": null
      }
    ]
  },
  {
    "case": "competitor",
    "input": "Our competitor reported a cybersecurity incident.",
    "facts": [
      {
        "metric": "CYBERSECURITY_INCIDENT",
        "kind": "EVENT",
        "period": null,
        "scope": "ISSUER",
        "span": "cybersecurity incident",
        "verification_reason": null
      }
    ]
  },
  {
    "case": "rumor",
    "input": "The CEO is rumored to resign.",
    "facts": [
      {
        "metric": "OFFICER_DEPARTURE",
        "kind": "EVENT",
        "period": null,
        "scope": "ISSUER",
        "span": "CEO is rumored to resign",
        "verification_reason": null
      }
    ]
  },
  {
    "case": "announced_future_departure",
    "input": "The CEO announced plans to resign effective November 30.",
    "facts": [
      {
        "metric": "HYPOTHETICAL:OFFICER_DEPARTURE",
        "kind": "EVENT",
        "period": null,
        "scope": "ISSUER",
        "span": "The CEO announced plans to resign effective November 30.",
        "verification_reason": null
      }
    ]
  },
  {
    "case": "numeric_control",
    "input": "Revenue for the third quarter of fiscal 2027 was $35.1 billion.",
    "claimed_kind": "REPORTED",
    "claimed_value": [
      351,
      10
    ],
    "verified": true,
    "reason": null,
    "verified_kind": "REPORTED",
    "verified_value": [
      351,
      10
    ]
  },
  {
    "case": "numeric_sign_flip",
    "input": "Revenue for the third quarter of fiscal 2027 was $35.1 billion.",
    "claimed_kind": "REPORTED",
    "claimed_value": "-35.1",
    "verified": true,
    "reason": null,
    "verified_kind": "REPORTED",
    "verified_value": [
      -351,
      10
    ]
  },
  {
    "case": "numeric_kind_flip",
    "input": "Revenue for the third quarter of fiscal 2027 was $35.1 billion.",
    "claimed_kind": "GUIDANCE",
    "claimed_value": [
      351,
      10
    ],
    "verified": true,
    "reason": null,
    "verified_kind": "GUIDANCE",
    "verified_value": [
      351,
      10
    ]
  },
  {
    "case": "hypothetical_assessment_1",
    "cutoff_ms": 1791590400000,
    "decision": "ACCEPT",
    "status": "ASSESSED",
    "statements": [
      {
        "event": "RESTATEMENT",
        "novelty": "NEW",
        "statement": "Any future restatement of our financial statements would harm investor confidence."
      },
      {
        "event": "IMPAIRMENT",
        "novelty": "NEW",
        "statement": "Goodwill impairment could result if the operating results of the segment decline."
      },
      {
        "event": "CYBERSECURITY_INCIDENT",
        "novelty": "NEW",
        "statement": "A cybersecurity incident could disrupt our operations."
      },
      {
        "event": "OFFICER_DEPARTURE",
        "novelty": "NEW",
        "statement": "Our Chief Executive Officer may resign at any time."
      },
      {
        "event": "DELISTING",
        "novelty": "NEW",
        "statement": "There is a risk that our common stock could be delisted from the exchange."
      },
      {
        "event": "IMPAIRMENT",
        "novelty": "NEW",
        "statement": "We expect to record an impairment charge in the fourth quarter."
      }
    ],
    "gate": "UNKNOWN",
    "gate_reasons": [
      "NEW_HYPOTHETICAL_EVENT"
    ],
    "reviews": [
      "REVIEW_NEW_HYPOTHETICAL_EVENT"
    ]
  },
  {
    "case": "hypothetical_assessment_2",
    "cutoff_ms": 1791612000000,
    "decision": "ACCEPT",
    "status": "ASSESSED",
    "statements": [
      {
        "event": "RESTATEMENT",
        "novelty": "NEW",
        "statement": "Any future restatement of our financial statements would harm investor confidence."
      },
      {
        "event": "IMPAIRMENT",
        "novelty": "NEW",
        "statement": "Goodwill impairment could result if the operating results of the segment decline."
      },
      {
        "event": "CYBERSECURITY_INCIDENT",
        "novelty": "NEW",
        "statement": "A cybersecurity incident could disrupt our operations."
      },
      {
        "event": "OFFICER_DEPARTURE",
        "novelty": "NEW",
        "statement": "Our Chief Executive Officer may resign at any time."
      },
      {
        "event": "DELISTING",
        "novelty": "NEW",
        "statement": "There is a risk that our common stock could be delisted from the exchange."
      },
      {
        "event": "IMPAIRMENT",
        "novelty": "NEW",
        "statement": "We expect to record an impairment charge in the fourth quarter."
      }
    ],
    "gate": "UNKNOWN",
    "gate_reasons": [
      "NEW_HYPOTHETICAL_EVENT"
    ],
    "reviews": [
      "REVIEW_NEW_HYPOTHETICAL_EVENT"
    ]
  },
  {
    "case": "expired_after_clear",
    "first_decision": "ACCEPT",
    "first_gate": "CLEAR",
    "first_expiry_ms": 1791594000000,
    "second_expiry_ms": 1791594000000,
    "now_ms": 1791594000001,
    "second_decision": "REJECT_EXPIRED",
    "after_gate": "CLEAR",
    "state_unchanged": true,
    "state_fields": [
      "accepted_keys",
      "accepted_result_ids",
      "availability",
      "context",
      "context_hash",
      "evidence_gate",
      "gate_reasons",
      "issuer_id",
      "latest_cutoff_ms",
      "max_known_facts",
      "policy_profile_hash",
      "schema",
      "unresolved_adverse",
      "version"
    ]
  }
]
```
