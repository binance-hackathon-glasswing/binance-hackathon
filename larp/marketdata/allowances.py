"""IDEA-096 F4: public, pinned six-token router allowance observation; never a wallet action."""
from types import SimpleNamespace

from larp.execution import USDT
from larp.marketdata.port import TOKENS


def observe(decoder, wallet):
    symbols = {USDT: 'USDT', **{t: s for s, t in TOKENS.items()}}
    amounts = decoder.allowances(SimpleNamespace(router=decoder.router, wallet=wallet))
    values = {symbols[t]: str(a) for t, a in amounts.items()}
    return dict(section='router_allowances', reason='DIRTY_ROUTER_ALLOWANCE' if any(amounts.values()) else 'CLEAN',
                severity='LOW', allowances=values, symbols=sorted(symbols[t] for t, a in amounts.items() if a))


def from_config(config):
    """Read-only operational export. Exceptions expose only a fixed status, never RPC/config text."""
    try:
        from larp.execution_live.chain import Rpc
        from larp.execution_live.main import router_decoder
        from larp.marketdata.web3 import Artifacts
        rpc = Rpc(config['rpc_url'], artifacts=Artifacts(config['chain_artifact_root']),
                  source_id=config['rpc_source_id'])
        return observe(router_decoder(config, rpc), config['wallet_address'])
    except Exception:
        return dict(section='router_allowances', reason='ALLOWANCE_READ_UNAVAILABLE', allowances=None, symbols=[])
