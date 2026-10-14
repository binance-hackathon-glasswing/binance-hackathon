"""Live evidence wiring (DR-12, B8; IDEA-041 parts 1 and 2): preflight, terms captures, the live poll runner, its
gap report, and the assessor bake-off on real filings.

    python -m larp.sources.live preflight
    python -m larp.sources.live terms [--write-register]
    python -m larp.sources.live run --hours 24 [--config-mode live]
    python -m larp.sources.live report --from <ISO> --to <ISO> [--incidents incidents.json]
    python -m larp.sources.live bakeoff --days 120 --per-issuer 5 --candidate anthropic:<model-id>:<effort> ...

Environment: `LARP_SEC_USER_AGENT` (a real contact, SEC fair access), `LARP_ARTIFACT_ROOT` (absolute, outside the
repository: raw bytes, saved text, SQLite stores, the poll log and reports), and for the bake-off
`LARP_ANTHROPIC_API_KEY` / `LARP_OPENAI_API_KEY`. Nothing here signs, trades or uploads round logs, and no source
record has trading authority. Every live mode refuses to start from a working tree with uncommitted changes
(code that affects decisions or logging runs only from a pushed commit; AGENTS.md).

The runner polls each enabled register source no more often than its `min_interval_ms`, and each issuer's EDGAR
filings every `--edgar-interval-ms` (requests spaced <= 5/s by the EDGAR adapter). Each poll appends one fsynced
JSON line to `<root>/live/polls.jsonl`; on restart the runner resumes cadence from that log. `gap_report` turns
the log into the DR-12 evidence: the longest gap between successful polls per target against twice its cadence,
with gaps explained only by listed incidents.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import sys
import time

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, sha256_hex

REPO = Path(__file__).resolve().parents[2]
LOG_NAME = "polls.jsonl"
OK_STATUSES = ("OK", "NOT_MODIFIED")
DEFAULT_EDGAR_INTERVAL_MS = 300_000
MAX_TERMS_BYTES = 4_000_000


def epoch_ms() -> int:
    return time.time_ns() // 1_000_000


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_state(repo: Path = REPO) -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    # Hidden index flags (assume-unchanged is lowercase, skip-worktree is "S") and an untracked-files
    # setting can each make plain status report a modified tree as clean.
    hidden = any(line[:1].islower() or line[:1] == "S" for line in git("ls-files", "-v").splitlines())
    dirty = hidden or bool(git("status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"))
    state = {"commit": git("rev-parse", "HEAD"), "dirty": dirty, "pushed": False}
    try:
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
        remote = git("config", "--get", f"branch.{branch}.remote")
        target = git("config", "--get", f"branch.{branch}.merge")
        if remote and remote != "." and not remote.startswith("-") and target.startswith("refs/heads/"):
            # Query the remote itself; a stale tracking ref is no proof of a push.
            # Never return a remote URL or git's stderr (either can contain credentials).
            reply = subprocess.run(["git", "ls-remote", "--exit-code", remote, target], cwd=repo,
                                   capture_output=True, text=True, timeout=30, check=True)
            state["pushed"] = any(line.split() == [state["commit"], target] for line in reply.stdout.splitlines())
    except (subprocess.SubprocessError, OSError):
        pass  # no upstream or no connectivity: refuse live execution
    return state


def release_state(manifest: str | None, root: str | None) -> dict:
    """The build a verified release manifest names, in git_state's shape; refuses an unverified release."""
    from larp.contracts import ContractError
    from larp.runtime.preflight import verify_release
    if not manifest or not root:
        raise SystemExit("A release run needs both --release-manifest and --release-root")
    try:
        verified = verify_release(Document(Path(manifest).read_bytes()), root)
    except (ContractError, ValueError, OSError):
        raise SystemExit("Refusing live execution: the release does not verify against its manifest") from None
    return {"commit": verified["build_id"], "dirty": False, "pushed": verified.get("remote_verified") is True}


def require_committed(state: dict, allow_dirty: bool) -> None:
    if state["dirty"]:
        raise SystemExit("Refusing to run live code from a working tree with uncommitted changes (commit and push first)")
    if state.get("pushed") is not True:
        raise SystemExit("Refusing live execution until HEAD is verified at its configured remote branch")


# ------------------------------------------------------------------------------------------------ terms captures
SEC_AGENT_ENV = "LARP_SEC_USER_AGENT"


def _agent_env(host: str, required: str | None) -> str | None:
    """The environment variable naming the User-Agent a terms fetch must declare: the source's own requirement, and
    the SEC contact for any sec.gov host (SEC fair access applies to the whole site)."""
    if required:
        return required
    return SEC_AGENT_ENV if host == "sec.gov" or host.endswith(".sec.gov") else None


def capture_terms(sources: dict, fetch, artifacts, clock_ms, *, user_agents: dict | None = None,
                  edgar: dict | None = None) -> list:
    """Fetch each enabled source's terms page (and the EDGAR path's, `edgar`), store its bytes and return dated rows
    with their SHA-256.

    `fetch(url, headers, timeout_s) -> (status, headers, body)` must not follow redirects; same-host https
    redirects are followed here (at most 3). A page on a host that needs a declared User-Agent (the source's
    requirement, or the SEC contact for sec.gov) is fetched with the agent from `user_agents` {env name: agent};
    with none configured it is not fetched (FAILED: USER_AGENT_NOT_CONFIGURED). Other hosts get the generic agent.
    Rows record failures too; a failed capture has no hash.
    """
    from urllib.parse import urljoin, urlsplit
    from larp.sources.transport import USER_AGENT_DEFAULT
    user_agents = user_agents or {}
    targets = [(s.source_id, s.rights["terms_url"], s.requires_user_agent)
               for s in sorted(sources.values(), key=lambda s: s.source_id) if s.enabled]
    if edgar is not None:
        targets.append((edgar["source_id"], edgar["terms_url"], edgar.get("requires_user_agent")))
    rows = []
    for source_id, terms_url, required in targets:
        url, host, row = terms_url, urlsplit(terms_url).hostname or "", None
        env_name = _agent_env(host, required)
        agent = user_agents.get(env_name) if env_name else USER_AGENT_DEFAULT
        for _ in range(4):
            if not agent:
                row = {"status": "FAILED", "error": "USER_AGENT_NOT_CONFIGURED"}
                break
            if urlsplit(url).scheme != "https" or urlsplit(url).hostname != host:
                row = {"status": "REFUSED", "error": "REDIRECT_OR_URL_NOT_SAME_HTTPS_HOST"}
                break
            try:
                status, headers, body = fetch(url, {"User-Agent": agent}, 30)
            except OSError as exc:
                row = {"status": "FAILED", "error": type(exc).__name__}
                break
            headers = {k.lower(): v for k, v in (headers or {}).items()}
            if status in (301, 302, 303, 307, 308):
                url = urljoin(url, headers.get("location", ""))
                continue
            if status != 200 or not body or len(body) > MAX_TERMS_BYTES:
                row = {"status": "FAILED", "error": f"HTTP_{status}" if status != 200 else "EMPTY_OR_TOO_LARGE"}
                break
            digest = artifacts.put(body)
            if digest != sha256_hex(body):
                raise IntelligenceError("Artifact store returned a different content address")
            row = {"status": "CAPTURED", "final_url": url, "content_type": headers.get("content-type"),
                   "bytes": len(body), "sha256": digest}
            break
        else:
            row = {"status": "FAILED", "error": "TOO_MANY_REDIRECTS"}
        now = clock_ms()
        rows.append({"source_id": source_id, "terms_url": terms_url, "user_agent_env": env_name,
                     "captured_ms": now, "captured_utc": iso(now), **row})
    return rows


def write_register_terms(path: Path, rows: list) -> list:
    """Set terms_evidence_sha256 and terms_checked (capture date) for each captured source, editing only those
    values in the register file so its layout and every other byte stay as they are. Returns updated IDs."""
    text, updated = path.read_text("utf-8"), []
    for row in rows:
        if row.get("status") != "CAPTURED":
            continue
        start = text.find(f'"source_id": "{row["source_id"]}"')
        end = text.find('"source_id": "', start + 1)
        end = len(text) if end < 0 else end
        block = text[start:end]
        block = re.sub(r'"terms_evidence_sha256": (?:null|"[0-9a-f]{64}")',
                       f'"terms_evidence_sha256": "{row["sha256"]}"', block, count=1)
        block = re.sub(r'"terms_checked": "[0-9-]+"', f'"terms_checked": "{row["captured_utc"][:10]}"', block, count=1)
        text = text[:start] + block + text[end:]
        updated.append(row["source_id"])
    json.loads(text)  # still valid JSON
    path.write_text(text, "utf-8")
    return updated


# ------------------------------------------------------------------------------------------------ poll log
class PollLog:
    """Append-only JSON lines, fsynced per line; the durable evidence of what was polled when."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, line: dict) -> None:
        """Append one record. If the file ends in a torn record (no final newline, e.g. after a crash mid-write), a
        newline is written first: the damaged bytes stay as they are and read back as one corrupt line, and this
        record stays a line of its own (IDEA-041 R04)."""
        data = (json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        with open(self.path, "a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() > 0:
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    data = b"\n" + data
            handle.seek(0, os.SEEK_END)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    def lines(self) -> list:
        if not self.path.exists():
            return []
        out = []
        for raw in self.path.read_bytes().split(b"\n"):
            if not raw:
                continue
            try:
                line = json.loads(raw.decode("utf-8"))
                if type(line) is not dict:
                    raise ValueError("not an object")
                out.append(line)
            except ValueError:  # a torn line after a crash is reported, not dropped silently
                out.append({"corrupt": True, "bytes": len(raw), "sha256": sha256_hex(raw)})
        return out


@dataclass(frozen=True)
class Target:
    key: str        # "source:<id>" or "edgar:<issuer_id>"
    cadence_ms: int


class LiveRunner:
    """Polls every target when due. `source_ingestor.poll(source_id)` and `edgar_ingestor.poll(issuer_id)` are the
    real ingestors (larp.sources.ingest.SourceIngestor, larp.intelligence.ingest.Ingestor)."""

    def __init__(self, *, register: dict, issuers: list, source_ingestor, edgar_ingestor, log: PollLog, clock_ms,
                 sleep=time.sleep, edgar_interval_ms: int = DEFAULT_EDGAR_INTERVAL_MS, commit: str = "unknown"):
        if edgar_interval_ms < 60_000:
            raise IntelligenceError("EDGAR polling more often than once a minute per issuer is not needed")
        self.targets = [Target(f"source:{s.source_id}", s.limits["min_interval_ms"])
                        for s in sorted(register.values(), key=lambda x: x.source_id) if s.enabled]
        self.targets += [Target(f"edgar:{i}", edgar_interval_ms) for i in sorted(issuers)]
        self.sources, self.edgar, self.log, self.clock, self.sleep = source_ingestor, edgar_ingestor, log, clock_ms, sleep
        self.commit = commit
        self.last = {}
        for line in log.lines():  # resume cadence after a restart
            if "target" in line and type(line.get("started_ms")) is int:
                self.last[line["target"]] = max(self.last.get(line["target"], 0), line["started_ms"])

    def due(self, now: int) -> list:
        return [t for t in self.targets if now - self.last.get(t.key, -10**15) >= t.cadence_ms]

    def poll(self, target: Target) -> dict:
        started = self.clock()
        kind, ident = target.key.split(":", 1)
        try:
            if kind == "source":
                outcome = self.sources.poll(ident)
                summary = {"status": outcome["status"], "pages": outcome.get("pages"),
                           "new": len(outcome.get("new", [])), "versions": len(outcome.get("versions", [])),
                           "withdrawn": len(outcome.get("withdrawn", [])), "rejected": len(outcome.get("rejected", [])),
                           "truncated": outcome.get("truncated"), "error": outcome.get("error")}
            else:
                outcome = self.edgar.poll(ident).read()
                summary = {"status": outcome["status"], "new": len(outcome.get("new_records", [])),
                           "revisions": len(outcome.get("revisions", [])), "late": len(outcome.get("late", [])),
                           "dead_letter": len(outcome.get("dead_letter", [])), "jobs": len(outcome.get("jobs", [])),
                           "error": (outcome.get("receipt") or {}).get("status") if outcome["status"] == "CONFLICT"
                           else None,
                           "coverage_complete": outcome.get("coverage_complete"),
                           "retry_pending": len(outcome.get("retry_pending", [])),
                           "malformed_rows": outcome.get("malformed_rows", 0),
                           "unexpected_forms": len(outcome.get("unexpected_forms", [])),
                           "rejected_future": len(outcome.get("rejected_future", []))}
        except Exception as exc:  # one failing target never stops the others; the failure is logged
            summary = {"status": "EXCEPTION", "error": type(exc).__name__}
        line = {"schema": "LivePoll.v1", "target": target.key, "cadence_ms": target.cadence_ms, "started_ms": started,
                "finished_ms": self.clock(), "commit": self.commit, **summary}
        self.log.append(line)
        self.last[target.key] = started
        return line

    def tick(self) -> list:
        return [self.poll(t) for t in self.due(self.clock())]

    def run(self, until_ms: int) -> int:
        polls = 0
        while self.clock() < until_ms:
            polls += len(self.tick())
            now = self.clock()
            waits = [self.last.get(t.key, now) + t.cadence_ms - now for t in self.targets]
            self.sleep(max(1.0, min(waits + [until_ms - now]) / 1000))
        return polls


def gap_report(lines: list, *, cadences: dict, start_ms: int, end_ms: int, incidents: list = (),
               required_ms: int = 86_400_000, tolerance: int = 2) -> dict:
    """DR-12 evidence from the poll log. A gap is the time between consecutive successful polls of one target (and
    from `start_ms` to the first, and from the last to `end_ms`); it is unexplained when it exceeds `tolerance` x
    cadence and no incident {target, from_ms, to_ms, reason} covers it. The cadence is the stricter of the declared
    one (`cadences`, which also names the targets) and the one the runner logged with the poll that opens the gap
    (the first logged one in the window for the gap from `start_ms`); so a run at a faster logged cadence is held
    to it, and a run that logged a slower cadence than declared cannot pass (IDEA-041 R13). The report lists the
    logged cadences per target. PASS needs a window of at least
    `required_ms`, no unexplained gap and no corrupt log line; a shorter window is INCONCLUSIVE."""
    corrupt = sum(1 for line in lines if line.get("corrupt"))
    targets = {}
    for key, declared in sorted(cadences.items()):
        mine = [l for l in lines if l.get("target") == key and type(l.get("started_ms")) is int]
        logged = {l["started_ms"]: l["cadence_ms"] for l in mine
                  if type(l.get("cadence_ms")) is int and l["cadence_ms"] > 0}
        def complete(line):
            finished = line.get("finished_ms", line["started_ms"])  # legacy log without a completion clock
            return (line.get("status") in OK_STATUSES and line.get("coverage_complete") is not False
                    and not any(line.get(k) for k in ("truncated", "rejected", "dead_letter", "retry_pending",
                                                       "malformed_rows", "unexpected_forms", "rejected_future"))
                    and type(finished) is int and line["started_ms"] <= finished <= end_ms)

        ok = sorted(l["started_ms"] for l in mine if complete(l) and start_ms <= l["started_ms"] <= end_ms)
        failures = sum(1 for l in mine if not complete(l) and start_ms <= l["started_ms"] <= end_ms)
        points = [start_ms] + ok + [end_ms]
        after = [t for t in logged if t >= start_ms]
        first = logged[min(after)] if after else declared  # the cadence the run logged at its first poll in the window
        gaps = []
        for a, b in zip(points, points[1:]):
            # The stricter of the logged and the declared cadence: a run that logs a slower cadence than the
            # declared one cannot pass by its own account (review of R13).
            cadence = min(logged.get(a, first if a == start_ms else declared), declared)
            if b - a > tolerance * cadence:
                cover = [i for i in incidents if i.get("target") in (key, "*") and i["from_ms"] <= a + cadence
                         and i["to_ms"] >= b - cadence]
                gaps.append({"from_ms": a, "to_ms": b, "gap_ms": b - a, "from_utc": iso(a), "to_utc": iso(b),
                             "explained_by": cover[0]["reason"] if cover else None})
        targets[key] = {"cadence_ms": declared, "logged_cadences_ms": sorted(set(logged.values())),
                        "slower_than_declared": any(c > declared for c in logged.values()),
                        "successful_polls": len(ok), "failed_polls": failures,
                        "max_gap_ms": max((b - a for a, b in zip(points, points[1:])), default=None),
                        "gaps_over_tolerance": gaps,
                        "unexplained_gaps": sum(1 for g in gaps if g["explained_by"] is None)}
    unexplained = sum(t["unexplained_gaps"] for t in targets.values())
    verdict = ("INCONCLUSIVE" if end_ms - start_ms < required_ms else
               "PASS" if not unexplained and not corrupt and targets else "FAIL")
    return {"schema": "LiveIngestionReport.v1", "window": {"from_utc": iso(start_ms), "to_utc": iso(end_ms),
                                                           "hours": round((end_ms - start_ms) / 3_600_000, 2)},
            "tolerance_x_cadence": tolerance, "verdict": verdict, "corrupt_log_lines": corrupt,
            "commits": sorted({l.get("commit") for l in lines if l.get("commit")}), "targets": targets}


# ------------------------------------------------------------------------------------------------ wiring
def preflight(env, config_mode: str = "live") -> list:
    """Source preflight plus the evidence path's own live parameters (null until the team sets them)."""
    from larp.intelligence.config import load_config
    from larp.sources.register import load_register, live_preflight
    reasons = live_preflight(load_register()[0], env)
    try:
        load_config(config_mode)
    except IntelligenceError as exc:
        reasons.append(f"INTELLIGENCE_CONFIG_REFUSED:{config_mode}:{exc}")
    return reasons


def _env_root(env, config_mode: str = "live") -> Path:
    reasons = preflight(env, config_mode)
    if reasons:
        raise SystemExit("Live preflight refused:\n  " + "\n  ".join(reasons))
    return Path(env["LARP_ARTIFACT_ROOT"]).resolve()


def build_runner(env, *, config_mode: str, edgar_interval_ms: int, commit: str, clock_ms=epoch_ms):
    from larp.intelligence.config import load_config, load_registry, sec_user_agent
    from larp.intelligence.edgar import EdgarHttpSource
    from larp.intelligence.ingest import Ingestor
    from larp.sources.ingest import SourceIngestor
    from larp.sources.register import load_register
    from larp.sources.store import FileArtifacts, SQLiteEvidenceStore, SQLiteSourceStore
    from larp.sources.transport import AllowlistedClient, urllib_fetch
    root = _env_root(env, config_mode)
    register, aliases, register_sha = load_register()
    config, registry = load_config(config_mode), load_registry()
    artifacts = FileArtifacts(str(root / "artifacts"))
    agent = sec_user_agent(env)
    sources = SourceIngestor(register=register, register_sha256=register_sha, aliases=aliases,
                             client=AllowlistedClient(urllib_fetch, user_agents={"LARP_SEC_USER_AGENT": agent}),
                             store=SQLiteSourceStore(str(root / "sources.sqlite")), artifacts=artifacts, clock_ms=clock_ms)
    edgar = Ingestor(registry=registry, source=EdgarHttpSource(agent, clock_ms=clock_ms),
                     store=SQLiteEvidenceStore(str(root / "evidence.sqlite")), artifacts=artifacts, config=config,
                     clock_ms=clock_ms, run_id=f"live-ingest:{commit[:12]}")
    return LiveRunner(register=register, issuers=[e.issuer_id for e in registry.entries], source_ingestor=sources,
                      edgar_ingestor=edgar, log=PollLog(root / "live" / LOG_NAME), clock_ms=clock_ms,
                      edgar_interval_ms=edgar_interval_ms, commit=commit)


def parse_candidate(spec: str) -> tuple:
    """'anthropic:<model-id>:<effort>' or 'openai:<model-id>:<effort>'."""
    parts = spec.split(":")
    if len(parts) != 3 or parts[0] not in ("anthropic", "openai"):
        raise SystemExit(f"Bad --candidate {spec!r}: expected provider:model-id:effort")
    return tuple(parts)


def parse_price(spec: str) -> tuple:
    """'<provider>:<model-id>=<input micro-USD per Mtok>,<output micro-USD per Mtok>,<source>'."""
    name, _, values = spec.partition("=")
    parts = values.split(",", 2)
    if len(parts) != 3:
        raise SystemExit(f"Bad --price {spec!r}")
    return name, {"input_micro_usd_per_mtok": int(parts[0]), "output_micro_usd_per_mtok": int(parts[1]),
                  "source": parts[2]}


def run_bakeoff(env, args, commit: str) -> dict:
    from larp.intelligence import bakeoff
    from larp.intelligence.agent import EMPTY_CONTEXT, EvidenceAssessor, build_request
    from larp.intelligence.config import LiveModelSettings, load_config, load_registry, sec_user_agent
    from larp.intelligence.edgar import EdgarHttpSource
    from larp.intelligence.ingest import Ingestor
    from larp.intelligence.models import RuleBaselineModel
    from larp.intelligence.providers import hosted_model
    from larp.intelligence.tools import PortEvidenceReader
    from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
    root = _env_root(env, args.config_mode)
    config, registry, clock = load_config(args.config_mode), load_registry(), epoch_ms
    artifacts = FileArtifacts(str(root / "artifacts"))
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    (root / "bakeoff").mkdir(parents=True, exist_ok=True)
    store = SQLiteEvidenceStore(str(root / "bakeoff" / f"evidence-{stamp}.sqlite"))
    ingestor = Ingestor(registry=registry, source=EdgarHttpSource(sec_user_agent(env), clock_ms=clock), store=store,
                        artifacts=artifacts, config=config, clock_ms=clock, run_id=f"bakeoff:{commit[:12]}")
    now = clock()
    window = (now - args.days * 86_400_000, now)
    chosen = []
    for entry in registry.entries:
        ingestor.poll(entry.issuer_id, mode="BACKFILL", window=window)
        current = [d.read() for d in store.records(entry.issuer_id)]
        current = [r for r in current if r["form_class"] == "CURRENT" and r["quality"] != "MISSING"]
        chosen += sorted(current, key=lambda r: r["original_ms"], reverse=True)[:args.per_issuer]
    chosen = sorted(chosen, key=lambda r: (r["issuer_id"], r["original_ms"]))[:args.max_filings]
    if len(chosen) < args.min_filings:
        print(f"warning: only {len(chosen)} filings found (target {args.min_filings}-{args.max_filings})",
              file=sys.stderr)
    profile_hash = sha256_hex(b"larp.bakeoff.policy-profile.v1")
    cutoff = clock()
    requests = []
    for record in chosen:
        cursor = store.read_cursor("sec-edgar", record["issuer_id"]).read()
        requests.append(build_request(
            job={"job_id": f"bakeoff:{record['accession']}"}, run_id=f"bakeoff:{stamp}", issuer_id=record["issuer_id"],
            records=[record], cutoff_ms=cutoff, context=EMPTY_CONTEXT, policy_profile_hash=profile_hash,
            allowed_tools=list(config.tools), tool_calls=config.max_tool_calls, deadline_ms=config.max_deadline_ms,
            source_health={"status": cursor["health"]["status"], "last_success_ms": cursor["health"]["last_success_ms"]}))
    prices = dict(parse_price(p) for p in args.price or [])
    candidates = {"rule-baseline": RuleBaselineModel(clock)}
    for provider, model_id, effort in map(parse_candidate, args.candidate or []):
        key = env.get({"anthropic": "LARP_ANTHROPIC_API_KEY", "openai": "LARP_OPENAI_API_KEY"}[provider])
        candidates[f"{provider}:{model_id}:{effort}"] = hosted_model(
            LiveModelSettings(provider, model_id, api_key=key), prompt_text=config.prompt_text,
            prompt_sha256=config.prompt_sha256, clock_ms=clock, artifacts=artifacts,
            price=prices.get(f"{provider}:{model_id}"), effort=effort)
    reader = PortEvidenceReader(store, artifacts)
    make = lambda model: EvidenceAssessor(registry=registry, reader=reader, model=model, config=config, clock_ms=clock)
    results = bakeoff.run(candidates, requests, make)
    report = bakeoff.report(results, baseline_name="rule-baseline", commit=commit, generated_ms=clock(),
                            filings=[{k: r[k] for k in ("issuer_id", "accession", "form", "record_id", "original_ms")}
                                     for r in chosen],
                            identities={n: m.identity.record() for n, m in candidates.items()})
    out = root / "bakeoff" / f"report-{stamp}.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", "utf-8")
    raw = root / "bakeoff" / f"results-{stamp}.json"
    raw.write_text(Document.from_dict({"results": results}).payload.decode("utf-8"), "utf-8")
    report["written_to"] = [str(out), str(raw)]
    return report


def main(argv=None, env=None) -> int:
    env = dict(os.environ if env is None else env)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--config-mode", default="live", choices=("live", "development"))
    terms = sub.add_parser("terms")
    terms.add_argument("--write-register", action="store_true", help="record captured hashes in the register file")
    run = sub.add_parser("run")
    run.add_argument("--hours", type=float, default=24.0)
    run.add_argument("--config-mode", default="live", choices=("live", "development"))
    run.add_argument("--edgar-interval-ms", type=int, default=DEFAULT_EDGAR_INTERVAL_MS)
    run.add_argument("--allow-dirty", action="store_true", help=argparse.SUPPRESS)  # retained syntax; no bypass
    # Hosts run a verified release bundle, not a git checkout (IDEA-047 V01): the manifest replaces the git check.
    run.add_argument("--release-manifest", help="verified release manifest (hosts without a git checkout)")
    run.add_argument("--release-root", help="release directory the manifest covers")
    rep = sub.add_parser("report")
    rep.add_argument("--from", dest="start", required=True)
    rep.add_argument("--to", dest="end", required=True)
    rep.add_argument("--incidents", help="JSON list of {target, from_ms, to_ms, reason}")
    rep.add_argument("--edgar-interval-ms", type=int, default=DEFAULT_EDGAR_INTERVAL_MS,
                     help="cadence for EDGAR log lines that logged none (each line's own cadence_ms is used)")
    bake = sub.add_parser("bakeoff")
    bake.add_argument("--days", type=int, default=120)
    bake.add_argument("--per-issuer", type=int, default=5)
    bake.add_argument("--min-filings", type=int, default=15)
    bake.add_argument("--max-filings", type=int, default=25)
    bake.add_argument("--candidate", action="append", help="provider:model-id:effort (repeatable)")
    bake.add_argument("--price", action="append", help="provider:model-id=in_micro_usd_per_mtok,out,source")
    bake.add_argument("--config-mode", default="live", choices=("live", "development"))
    bake.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    from larp.sources.register import CONFIG as REGISTER, load_register
    if args.command == "preflight":
        reasons = preflight(env, args.config_mode)
        print(json.dumps({"schema": "LivePreflight.v1", "ok": not reasons, "refusals": reasons}, indent=1))
        return 1 if reasons else 0
    if args.command == "terms":
        from larp.sources.store import FileArtifacts
        from larp.sources.transport import urllib_fetch
        root = env.get("LARP_ARTIFACT_ROOT")
        if not root:
            raise SystemExit("LARP_ARTIFACT_ROOT is required (terms bytes are stored outside Git)")
        from larp.intelligence.config import sec_user_agent
        from larp.sources.register import load_edgar_terms
        register = load_register()[0]
        agents = {s.requires_user_agent: env[s.requires_user_agent] for s in register.values()
                  if s.requires_user_agent and env.get(s.requires_user_agent)}
        try:
            agents[SEC_AGENT_ENV] = sec_user_agent(env)  # a real SEC contact, never a placeholder
        except IntelligenceError:
            agents.pop(SEC_AGENT_ENV, None)
        rows = capture_terms(register, urllib_fetch, FileArtifacts(str(Path(root) / "artifacts")), epoch_ms,
                             user_agents=agents, edgar=load_edgar_terms())
        if args.write_register:
            for source_id in write_register_terms(REGISTER, rows):
                print(f"register updated: {source_id}", file=sys.stderr)
        print(json.dumps({"schema": "TermsCapture.v1", "rows": rows}, indent=1))
        return 0 if all(r["status"] == "CAPTURED" for r in rows) else 1
    if args.command == "report":
        if not env.get("LARP_ARTIFACT_ROOT"):
            raise SystemExit("LARP_ARTIFACT_ROOT is required (the poll log lives there)")
        root = Path(env["LARP_ARTIFACT_ROOT"]).resolve()
        start = int(datetime.fromisoformat(args.start.replace("Z", "+00:00")).timestamp() * 1000)
        end = int(datetime.fromisoformat(args.end.replace("Z", "+00:00")).timestamp() * 1000)
        cadences = {f"source:{s.source_id}": s.limits["min_interval_ms"]
                    for s in load_register()[0].values() if s.enabled}
        from larp.intelligence.config import load_registry
        cadences.update({f"edgar:{e.issuer_id}": args.edgar_interval_ms for e in load_registry().entries})
        incidents = json.loads(Path(args.incidents).read_text("utf-8")) if args.incidents else []
        report = gap_report(PollLog(root / "live" / LOG_NAME).lines(), cadences=cadences, start_ms=start, end_ms=end,
                            incidents=incidents)
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if report["verdict"] == "PASS" else 1
    if args.command == "run" and (args.release_manifest or args.release_root):
        state = release_state(args.release_manifest, args.release_root)
    else:
        state = git_state()
    require_committed(state, args.allow_dirty)
    if args.command == "run":
        runner = build_runner(env, config_mode=args.config_mode, edgar_interval_ms=args.edgar_interval_ms,
                              commit=state["commit"] + ("+dirty" if state["dirty"] else ""))
        polls = runner.run(epoch_ms() + int(args.hours * 3_600_000))
        print(json.dumps({"polls": polls, "log": str(runner.log.path)}))
        return 0
    report = run_bakeoff(env, args, state["commit"] + ("+dirty" if state["dirty"] else ""))
    print(json.dumps({k: report[k] for k in ("commit", "candidates", "written_to")}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
