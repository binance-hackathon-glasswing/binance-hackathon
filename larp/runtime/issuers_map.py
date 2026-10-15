"""IDEA-058: the `driver.issuers` map for runtime.json, from the Web3 token metadata and the issuer registry.

Each registry issuer maps to `{"token": <bStock>, "underlying_id": <the market's underlyingTicker>}`, keyed by its
canonical issuer ID (#25). A pair is written only if the evidence contract's own rule accepts it
(`larp.integration.contract._issuer_matches` with the market's source), so real filings are not later refused as the
wrong issuer. One read of `market/rwa/tokens`; nothing else is called.

    python -m larp.runtime.issuers_map --address 0x<public> --output issuers.json
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from larp.contracts import ContractError


def build_issuers_map(market):
    """({issuer_id: {token, underlying_id}}, provenance) from `market` (a MarketPort)."""
    from larp.integration.contract import _issuer_matches
    from larp.intelligence.config import CONFIG_DIR, load_registry
    metadata = market.metadata()  # refuses a missing, duplicate or misidentified token row
    registry = load_registry()
    mapping, artifact = {}, None
    for entry in registry.entries:
        row, record = metadata[entry.token]
        artifact = record['artifact_sha256']
        ticker = row.get('underlyingTicker')
        if type(ticker) is not str or not ticker.strip():
            raise ContractError(f'{entry.token}: the market names no underlying ticker')
        meta = {'token': entry.token, 'underlying_id': ticker}
        if not _issuer_matches({'issuer_id': entry.issuer_id, **meta}, ticker, source_id='BINANCE_WEB3'):
            listed = sorted(s.security_id for s in entry.securities)
            raise ContractError(f'{entry.token}: market ticker {ticker!r} is not a security the registry lists for '
                                f'{entry.issuer_id} ({", ".join(listed)})')
        mapping[entry.issuer_id] = meta
    registry_path = Path(CONFIG_DIR) / 'issuers.v1.json'
    provenance = dict(schema='IssuersMapProvenance.v1', metadata_artifact_sha256=artifact,
                      registry_sha256=hashlib.sha256(registry_path.read_bytes()).hexdigest())
    return mapping, provenance


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--address', required=True, help='any public address (metadata reads check no balance)')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    provenance_path = output.with_name(output.name + '.provenance.json')
    if output.exists() or provenance_path.exists():
        print(f'refused: {output} or its provenance exists; the map is never replaced', file=sys.stderr)
        return 2
    if client is None:
        key, secret = os.environ.get('BINANCE_API_KEY'), os.environ.get('BINANCE_SECRET_KEY')
        if not key or not secret:
            print('BINANCE_API_KEY / BINANCE_SECRET_KEY are not set; nothing was called', file=sys.stderr)
            return 2
        from larp.marketdata.web3 import Artifacts, Web3Client
        client = Web3Client(key, secret, artifacts=Artifacts(str(output.parent / (output.name + '.artifacts'))))
    from larp.marketdata.port import MarketPort
    from larp.marketdata.web3 import Unavailable
    try:
        mapping, provenance = build_issuers_map(MarketPort(client, args.address))
    except (ContractError, Unavailable, KeyError, TypeError, ValueError) as refused:
        print('refused:', refused, file=sys.stderr)
        return 2
    output.write_text(json.dumps(mapping, indent=2, sort_keys=True) + '\n')
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + '\n')
    print(f'{len(mapping)} issuers -> {output} (paste as driver.issuers in runtime.json)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
