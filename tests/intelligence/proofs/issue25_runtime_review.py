"""A-REQ-020/022: cross-owner failing proof for D's runtime review-job mapping.

Run explicitly; it is not part of pytest discovery because A cannot edit the owning implementation.
Uses real policy, snapshot and mapper with synthetic external market data only. Failure remains a
blocking finding even when the default component suite is green.
"""
from dataclasses import replace
from datetime import datetime, timezone
from larp.contracts import Document
from larp.intelligence.config import load_registry
from larp.integration.runtime import RuntimePlanner
from larp.marketdata.port import MarketPort
from larp.research.fixtures import snapshot, changed
from larp.strategy.policy import decide
from tests.marketdata.test_live_port import Client


def main():
    s = snapshot(held={'NVDAB': 2000}, now=datetime(2026, 10, 11, 16, tzinfo=timezone.utc))
    s = replace(s, policy_state=replace(s.policy_state, data=Document.from_dict(
        {'lifecycle': {'NVDAB': {'last_review_session': 70}}})))
    s = changed(s, markets=[m for m in MarketPort(Client(), '0x' + '1' * 40)(0)
                            if m['symbol'] in s.universe])
    ledger = s.context.read()['portfolio']
    for position in ledger['positions'].values():
        position['units'] *= 10**14  # preserve quantity while matching actual 18-decimal token metadata
        position['decimals'] = 18
    s = changed(s, portfolio=ledger)
    proposal = decide(s, s.policy_state)
    jobs = RuntimePlanner(job_validity_ms=86400000, job_max_attempts=3)._jobs(s, proposal, int(s.observed_at.timestamp()*1000))
    wanted = load_registry().by_token('NVDAB').issuer_id
    actual = [j['payload']['issuer_id'] for j in jobs if j['payload']['reason'] == 'HORIZON_REASSESSMENT']
    print({'required_issuer': wanted, 'actual_job_issuers': actual})
    assert actual == [wanted], 'Market security ticker cannot be used as evidence scheduler issuer ID'


if __name__ == '__main__':
    main()
