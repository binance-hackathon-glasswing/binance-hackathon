"""S1 Class 2 facts from accepted durable evidence, never raw model labels.

Official trade-restriction/suspension producers are not implemented here. This
adapter's scope is explicit; it does not qualify a complete live S1 input set.
"""
from larp.integration.contract import accept_records, red_flag_directives
from larp.intelligence.common import digest
from larp.strategy.s1 import EVIDENCE_WINDOW_SESSIONS


def exposure_inputs(*, records, profile, run_id, profile_hash, now_ms, markets,
                    known_versions, universe, session, calendar):
    accepted, rejected = accept_records(records, run_id=run_id, profile_hash=profile_hash,
        now_ms=now_ms, markets=markets, known_versions=known_versions, profile=profile, universe=universe)
    complete = (bool(universe) and not rejected and set(accepted) == set(universe)
                and all(r.get('quality') == 'VERIFIED' and r.get('availability') == 'AVAILABLE'
                        and r['status'] in ('CLEAR', 'ADVERSE') for r in accepted.values()))
    items, decisions = {}, list(rejected)
    sessions = getattr(calendar, 'sessions', ())
    for symbol, record in sorted(accepted.items()):
        directives = {(d['predicate_id'], d['accession']) for d in red_flag_directives(record, profile)
                      if d['class'] == 2 and d['kind'] == 'BLOCK_NEW_BUYS'}
        for finding in record['falsifier_findings']:
            flag = finding.get('red_flag') or {}
            if (flag.get('predicate_id'), flag.get('accession')) not in directives:
                continue
            event = flag.get('event_original_ms')
            # Never redate old evidence to its re-review/arrival time. Frozen
            # calendar opens define the same session clock used by policy.
            eligible = [i for i, opened, _ in sessions if type(event) is int and opened <= event]
            sid = max(eligible) if eligible and event <= now_ms else None
            if sid is None or not session - EVIDENCE_WINDOW_SESSIONS < sid <= session:
                decisions.append(dict(symbol=symbol, reason='OUT_OF_WINDOW_EVENT', finding_id=finding['finding_id']))
                continue
            accession = flag.get('amends_accession') if flag.get('amendment') else flag.get('accession')
            if not accession:
                complete = False
                decisions.append(dict(symbol=symbol, reason='ORIGINAL_ACCESSION_MISSING'))
                continue
            identity = dict(symbol=symbol, predicate_id=flag['predicate_id'],
                predicate_version=flag['predicate_version'], set_sha256=flag['set_sha256'], accession=accession)
            eid = digest('larp.s1.class2-evidence.v1', identity)
            items[eid] = dict(evidence_id=eid, verified=True, **{'class': 'CLASS_2_RED_FLAG'},
                             symbols=[symbol], session_index=sid)
    evidence = [items[k] for k in sorted(items)]
    return dict(schema='S1ExposureInput.v1', scope='ENABLED_CLASS2_FILINGS_ONLY', complete=complete,
        evidence=evidence, decisions=decisions,
        contexts={s: r['context_hash'] for s, r in sorted(accepted.items())},
        input_hash=digest('larp.s1.exposure-input.v1', dict(evidence=evidence, complete=complete,
                                                        contexts={s: r['context_hash'] for s, r in sorted(accepted.items())})))
