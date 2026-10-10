"""Independently labelled real-document evaluation (IDEA-030 T01, IDEA-031 AC-E04). Status today: NOT_RUN.

    python -m larp.intelligence.realeval --manifest <path outside the repo> [--out <path outside the repo>]

Input is a RealEvalManifest.v1 kept outside Git (private label data never enters the repository, F-61):
rights-cleared documents with their SHA-256 and split (SAFETY | DEV | HELD_OUT), labels written by annotators
who are not the implementers, frozen at a commit before predictions are made, and per-document expected
outputs: issuer occurrence findings, statements by (event, assertion), and numerical facts. The criteria are
frozen in config/intelligence/real_eval_criteria.v1.json.

The deterministic extractor/verifier is scored here; a model arm can be scored on identical inputs only once an
authorised no-additional-cost model exists. Without a manifest the report is NOT_RUN; a synthetic, non-independent,
rights-uncleared or tampered manifest is REFUSED. Synthetic fixtures can never satisfy this gate.
"""

from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json
import math

from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.facts import extract_document, is_statement, statement_event
from larp.intelligence.text import document_text

REPO = Path(__file__).resolve().parents[2]
SPLITS = ("SAFETY", "DEV", "HELD_OUT")


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list | None:
    """Wilson score interval [low, high] as floats rounded to 6 places; None without observations."""
    if total == 0:
        return None
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0.0, centre - half), 6), round(min(1.0, centre + half), 6)]


def admissible(manifest: dict, criteria: dict) -> list:
    """Reasons the manifest cannot be used for the T01 gate (empty = admissible)."""
    reasons = []
    if manifest.get("schema") != "RealEvalManifest.v1":
        return ["SCHEMA"]
    if manifest.get("synthetic") is not False:
        reasons.append("SYNTHETIC_NOT_ADMISSIBLE")
    labels = manifest.get("labels") or {}
    annotators, implementers = set(labels.get("annotators") or []), set(labels.get("implementers") or [])
    a = criteria["admissibility"]
    if len(annotators) < a["min_annotators"]:
        reasons.append("TOO_FEW_ANNOTATORS")
    if annotators & implementers or not implementers:
        reasons.append("ANNOTATORS_NOT_INDEPENDENT_OF_IMPLEMENTERS")
    if len(labels.get("frozen_commit") or "") != 40 or not labels.get("frozen_before_predictions"):
        reasons.append("LABELS_NOT_FROZEN_BEFORE_PREDICTIONS")
    docs = manifest.get("documents") or []
    if sum(1 for d in docs if d.get("split") == "HELD_OUT") < a["min_held_out_documents"]:
        reasons.append("TOO_FEW_HELD_OUT_DOCUMENTS")
    for d in docs:
        if d.get("split") not in SPLITS:
            reasons.append("UNKNOWN_SPLIT")
        if (d.get("rights") or {}).get("cleared") is not True or not (d.get("rights") or {}).get("licence_id"):
            reasons.append("RIGHTS_NOT_CLEARED")
        path = Path(d.get("path", "")).resolve()
        if REPO == path or REPO in path.parents:
            reasons.append("DOCUMENT_INSIDE_REPOSITORY")
    return sorted(set(reasons))


def predict(text: str, entry, source: dict, *, issuer_source: bool) -> dict:
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    facts = extract_document(text, sha, entry, source, issuer_source=issuer_source)
    return {"findings": sorted({f["metric"] for f in facts if f["kind"] == "EVENT" and not is_statement(f["metric"])}),
            "statements": sorted([statement_event(f["metric"]), f["statement"]["assertion"]]
                                 for f in facts if is_statement(f["metric"])),
            "numbers": sorted([f["metric"], f["kind"], f["period"], str(f["value"] or f["range"])]
                              for f in facts if f["kind"] != "EVENT")}


def score(rows: list) -> dict:
    """rows: [{"doc_id", "split", "expected": {...}, "predicted": {...}}] -> per-class counts and Wilson intervals."""
    out = {}
    for cls in ("findings", "statements", "numbers"):
        tp = fp = fn = 0
        false_positives = []
        for row in rows:
            want = [tuple(x) if type(x) is list else x for x in row["expected"].get(cls, [])]
            got = [tuple(x) if type(x) is list else x for x in row["predicted"].get(cls, [])]
            remaining = list(want)
            for g in got:
                if g in remaining:
                    remaining.remove(g)
                    tp += 1
                else:
                    fp += 1
                    false_positives.append([row["doc_id"], g])
            fn += len(remaining)
        out[cls] = {"tp": tp, "fp": fp, "fn": fn, "precision": wilson(tp, tp + fp), "recall": wilson(tp, tp + fn),
                    "precision_point": None if tp + fp == 0 else [tp, tp + fp],
                    "false_positives": false_positives[:200]}
    return out


def run(manifest_path: str | None, registry=None, criteria_path: Path = CONFIG_DIR / "real_eval_criteria.v1.json") -> dict:
    criteria = json.loads(criteria_path.read_text(encoding="utf-8"))
    base = {"schema": "RealEvalReport.v1", "criteria_sha256": hashlib.sha256(criteria_path.read_bytes()).hexdigest(),
            "promotion_authorized": False}
    if not manifest_path or not Path(manifest_path).exists():
        return dict(base, status="NOT_RUN", reason="NO_INDEPENDENTLY_LABELLED_RIGHTS_CLEARED_MANIFEST")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    reasons = admissible(manifest, criteria)
    if reasons:
        return dict(base, status="REFUSED", reasons=reasons)
    rows = []
    for d in manifest["documents"]:
        raw = Path(d["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != d["sha256"]:
            return dict(base, status="REFUSED", reasons=["DOCUMENT_HASH_MISMATCH"])
        saved = document_text(raw, Path(d["path"]).name, d.get("content_type"))
        entry = registry.by_issuer(d["issuer_id"]) if registry is not None and d.get("issuer_id") else None
        source = {"record_id": d["doc_id"], "accession": d.get("accession"), "doc_name": Path(d["path"]).name,
                  "available_ms": d.get("available_ms"), "original_ms": d.get("original_ms")}
        rows.append({"doc_id": d["doc_id"], "split": d["split"], "expected": manifest["labels"]["items"][d["doc_id"]],
                     "predicted": predict(saved.text, entry, source, issuer_source=d.get("issuer_source", True))})
    held, safety = [r for r in rows if r["split"] == "HELD_OUT"], [r for r in rows if r["split"] == "SAFETY"]
    held_scores, safety_scores = score(held), score(safety)
    gates = criteria["held_out"]
    checks = {
        "safety_false_issuer_occurrences": safety_scores["findings"]["fp"] <= criteria["safety_set"]["max_false_issuer_occurrences"],
        "issuer_occurrence_precision": (held_scores["findings"]["precision"] or [0])[0]
        >= float(Fraction(*gates["issuer_occurrence_precision_lower_bound_min"])),
        "statement_precision": (held_scores["statements"]["precision"] or [0])[0]
        >= float(Fraction(*gates["statement_assertion_precision_lower_bound_min"])),
        "numeric_precision": (held_scores["numbers"]["precision"] or [0])[0]
        >= float(Fraction(*gates["numeric_precision_lower_bound_min"])),
    }
    return dict(base, status="PASS" if all(checks.values()) else "FAIL", checks=checks, held_out=held_scores,
                safety=safety_scores, documents=len(rows), arm="DETERMINISTIC_EXTRACTOR",
                model_arm={"status": "NOT_RUN", "reason": "NO_AUTHORISED_NO_COST_MODEL"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest")
    parser.add_argument("--out")
    args = parser.parse_args()
    from larp.intelligence.config import load_registry
    report = run(args.manifest, load_registry())
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        out = Path(args.out).resolve()
        if REPO in out.parents:
            raise SystemExit("--out must be outside the repository (label data stays out of Git)")
        out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
