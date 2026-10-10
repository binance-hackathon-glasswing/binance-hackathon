"""Training gate for the optional small evidence model (IDEA-007 Track A). Status: NOT RUN.

No model is trained here. `check_training_manifest` states what must exist before training
may start and returns NOT_RUN with the missing items until all of them do. Requirements
come from IDEA-007 §3/§7, IDEA-008 §4 and PARALLEL_BUILD.md:

- labels: rights-cleared, human or rule labelled; never Claude-generated (Anthropic AUP bans
  using Claude outputs to train models; IDEA-007 §1), never derived from future returns;
- a committed experiment record (pre-registered criteria, chronological split, kill criteria);
- the base checkpoint's id, revision, SHA-256 and licence, and any teacher's output rights;
- a dataset manifest hash (data stays outside Git, F-61) and the compute/budget.

The synthetic evaluation pack in scenarios.py is Claude-authored and evaluation-only: it
must never be used as training data.
"""

from larp.intelligence.common import is_hash

REQUIRED = ("label_rights_reference", "label_source", "experiment_record_commit", "base_checkpoint_id",
            "base_checkpoint_revision", "base_checkpoint_sha256", "base_checkpoint_licence",
            "dataset_manifest_sha256", "compute", "budget")
FORBIDDEN_LABEL_SOURCES = ("claude", "anthropic", "synthetic-eval-pack", "future-returns")


def check_training_manifest(manifest: dict | None) -> dict:
    manifest = manifest or {}
    missing = [k for k in REQUIRED if not manifest.get(k)]
    problems = []
    for key in ("base_checkpoint_sha256", "dataset_manifest_sha256"):
        if manifest.get(key) and not is_hash(manifest[key]):
            problems.append(f"{key}_NOT_SHA256")
    source = str(manifest.get("label_source", "")).lower()
    if any(word in source for word in FORBIDDEN_LABEL_SOURCES):
        problems.append("LABEL_SOURCE_NOT_PERMITTED")
    teacher = str(manifest.get("teacher", "none")).lower()
    if any(word in teacher for word in ("claude", "anthropic")):
        problems.append("TEACHER_NOT_PERMITTED")
    if teacher not in ("", "none") and not manifest.get("teacher_output_rights_reference"):
        missing.append("teacher_output_rights_reference")
    ready = not missing and not problems
    return {"status": "READY_FOR_REVIEW" if ready else "NOT_RUN", "missing": missing, "problems": problems,
            "note": "Training additionally needs team approval (GAP-57); readiness here is not approval."}
