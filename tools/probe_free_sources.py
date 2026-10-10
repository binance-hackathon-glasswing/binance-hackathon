"""Read-only connectivity probe of the free-source endpoints (IDEA-031 AC-D09).

One unauthenticated GET per enabled source through the allowlisted client (FTC is probed with a probe-only
copy of its disabled definition, to record whether its tested path still fails). Prints status, content
type, size, item count and the first item's timestamp fields. Stores no article bodies anywhere and writes
nothing to the repository. A successful response is not an uptime, latency or completeness result.

    python tools/probe_free_sources.py [--out <path outside the repo>]

The SEC endpoint needs LARP_SEC_USER_AGENT (a real contact); without it SEC is reported SKIPPED.
"""

from dataclasses import replace
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from larp.sources.parse import parse  # noqa: E402
from larp.sources.register import load_register  # noqa: E402
from larp.sources.transport import AllowlistedClient, SourceError, urllib_fetch  # noqa: E402

TIME_FIELDS = ("published_raw", "event_times", "changed_raw", "doc_type")


def probe(source, client) -> dict:
    started = time.time()
    row = {"source_id": source.source_id, "url": source.listing_url, "enabled_in_register": source.enabled,
           "probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))}
    try:
        response = client.get(source, source.listing_url)
        items, next_url = parse(source, response.body, response.url)
        row.update(status=response.status, attempts=response.attempts, bytes=len(response.body or b""),
                   content_type=response.headers.get("content-type"), items=len(items), has_next_page=bool(next_url),
                   first_item={k: items[0].get(k) for k in TIME_FIELDS} if items else None,
                   first_item_has_body=bool(items and items[0].get("body_html")))
    except SourceError as exc:
        row.update(status="FAILED", error=str(exc))
    row["elapsed_ms"] = int((time.time() - started) * 1000)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", help="write the JSON summary here (must be outside the repository)")
    args = parser.parse_args()
    register, _, register_sha = load_register()
    agents = {"LARP_SEC_USER_AGENT": os.environ.get("LARP_SEC_USER_AGENT")}
    client = AllowlistedClient(urllib_fetch, user_agents=agents)
    rows = []
    for source in register.values():
        if source.source_id == "ftc-press":
            source = replace(source, enabled=True)  # probe only; the register keeps FTC disabled
        elif not source.enabled:
            continue
        if source.requires_user_agent and not agents.get(source.requires_user_agent):
            rows.append({"source_id": source.source_id, "status": "SKIPPED", "error": "USER_AGENT_NOT_CONFIGURED"})
            continue
        rows.append(probe(source, client))
    report = {"schema": "FreeSourceProbe.v1", "register_sha256": register_sha, "rows": rows,
              "note": "One read-only request per endpoint; no bodies stored; not an uptime or latency measurement."}
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        out = Path(args.out).resolve()
        if Path(__file__).resolve().parents[1] in out.parents:
            raise SystemExit("--out must be outside the repository")
        out.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
