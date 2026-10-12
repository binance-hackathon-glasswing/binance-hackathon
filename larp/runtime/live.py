"""Live-mode start checks and the final-wallet switch (IDEA-042 W1-W3; DR-17, GAP-52, G-09).

`check_live_start` runs before a `dev` or `live` runtime opens a session. It refuses, naming the reason but never a
secret value, when a port is a fake, a required secret is missing, a wallet key sits on the runtime host, the
addresses disagree, or a record directory belongs to another wallet. `offline` and `paper` modes are not checked here:
they have no signing capability (larp/runtime/release.py).

`switch_wallet` moves the runtime from the development wallet to the registered final wallet (F-14): a fresh run with
its own `.ai-seeds/` and nonce directories, opened only once the old run is closed, unreserved and flat.
"""

from pathlib import Path
import re

from larp.contracts import ContractError

ADDRESS = re.compile(r'^0x[0-9a-fA-F]{40}$')
# The runtime host holds API and log credentials only; the wallet key lives on the isolated signer host.
RUNTIME_SECRETS = ('AI_SEEDS_ADDRESS', 'AI_SEEDS_SECRET', 'BINANCE_API_KEY', 'BINANCE_SECRET_KEY')
SIGNER_ONLY = ('WALLET_PRIVATE_KEY', 'WALLET_MNEMONIC')
MARKER = '.larp-wallet'
LIVE_MODES = ('dev', 'live')


class LiveStartRefused(ContractError):
    pass


def is_fake(port):
    """Fixtures declare themselves (`synthetic = True` or `mode = "fake"`) or live in a fixtures/fakes module."""
    module = type(port).__module__ or ''
    return (getattr(port, 'synthetic', False) is True or getattr(port, 'mode', None) == 'fake'
            or module.split('.')[-1] in ('fixtures', 'fakes', 'execution_fixtures')
            or type(port).__name__.startswith(('Fake', 'Scripted')))


def bind_directory(path, address):
    """Mark `path` as belonging to `address`; refuse a directory already marked for another wallet (G-09)."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    marker = path / MARKER
    if marker.exists():
        owner = marker.read_text(encoding='utf-8').strip()
        if owner != address.lower():
            raise LiveStartRefused(f'{path} belongs to another wallet')
        return path
    if any(p.name != MARKER for p in path.iterdir()):
        raise LiveStartRefused(f'{path} holds unmarked records; refusing to adopt them for a wallet')
    marker.write_text(address.lower() + '\n', encoding='utf-8')
    return path


def check_live_start(*, mode, ports, secrets, wallet_address, run_wallet, ai_seeds_dir, nonce_dir):
    """Raise LiveStartRefused unless a dev/live runtime may start. `ports`: name -> object; `secrets`: name -> value."""
    if mode not in ('offline', 'paper', 'dev', 'live'):
        raise LiveStartRefused('Unknown runtime mode')
    if mode not in LIVE_MODES:
        return
    fakes = sorted(name for name, port in ports.items() if port is None or is_fake(port))
    if fakes:
        raise LiveStartRefused('Fake or missing ports in live mode: ' + ', '.join(fakes))
    missing = [name for name in RUNTIME_SECRETS if not str(secrets.get(name) or '').strip()]
    if missing:
        raise LiveStartRefused('Missing runtime secrets: ' + ', '.join(missing))
    present = [name for name in SIGNER_ONLY if secrets.get(name)]
    if present:
        raise LiveStartRefused('Wallet key present on the runtime host (signer host only): ' + ', '.join(present))
    addresses = {'AI_SEEDS_ADDRESS': secrets['AI_SEEDS_ADDRESS'], 'configured wallet': wallet_address,
                 'run wallet': run_wallet}
    if any(type(v) is not str or not ADDRESS.fullmatch(v) for v in addresses.values()):
        raise LiveStartRefused('Wallet addresses must be 0x-prefixed 40-hex addresses')
    if len({v.lower() for v in addresses.values()}) != 1:
        raise LiveStartRefused('Wallet address mismatch between ' + ', '.join(sorted(addresses)))
    if Path(ai_seeds_dir).resolve() == Path(nonce_dir).resolve():
        raise LiveStartRefused('The .ai-seeds and nonce records need separate directories')
    for directory in (ai_seeds_dir, nonce_dir):
        bind_directory(directory, wallet_address)


def switch_wallet(store, *, old_run, new_run, new_wallet, chain_id, initial_projection, old_dirs, new_dirs):
    """Open the final wallet's run after the development run is closed and flat. Returns the switch record."""
    from larp.contracts import Document
    old = store.load(old_run).read()
    if not ADDRESS.fullmatch(new_wallet) or new_wallet.lower() == old['wallet_id'].lower():
        raise LiveStartRefused('The final wallet must be a new, valid address')
    if store.open_rounds(old_run):
        raise LiveStartRefused('Old run still has open rounds')
    if old['reservations']:
        raise LiveStartRefused('Old run still holds reservations')
    with store.transaction() as db:
        pending = db.execute("SELECT count(*) FROM commands WHERE run_id=%s AND status='PENDING'",
                             (old_run,)).fetchone()[0]
    if pending:
        raise LiveStartRefused('Old run still has pending execution commands')
    held = {k: v for k, v in (old['projection'].get('balances') or {}).items() if k not in ('USDT', 'BNB') and v}
    if held:
        raise LiveStartRefused('Old run is not flat: ' + ', '.join(sorted(held)))
    resolved = {Path(d).resolve() for d in old_dirs}
    if any(Path(d).resolve() in resolved for d in new_dirs) or len({Path(d).resolve() for d in new_dirs}) != 2:
        raise LiveStartRefused('The final wallet needs its own .ai-seeds and nonce directories')
    for directory in new_dirs:
        bind_directory(directory, new_wallet)
    head = store.verify(old_run)
    store.initialize(new_run, new_wallet.lower(), chain_id, Document.from_dict(initial_projection), mode='live')
    return dict(schema='WalletSwitch.v1', old_run=old_run, old_wallet=old['wallet_id'], old_head=head,
                old_version=old['version'], new_run=new_run, new_wallet=new_wallet.lower(),
                new_dirs=[str(Path(d)) for d in new_dirs])
