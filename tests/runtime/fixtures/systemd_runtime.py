"""WR-T7/8 inert external boundaries, executed only inside the disposable systemd unit."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

from larp.runtime import service
from larp.storage.postgres import PostgresStore


class CycleRecorder:
    ports = {}

    def once(self, now_ms):
        Path('/var/lib/larp-runtime/cycle').write_text(str(now_ms))


if __name__ == '__main__':
    connection, config_path, manifest, root = sys.argv[1:]
    config = json.loads(Path(config_path).read_text())
    store = PostgresStore(Path(connection).read_text())
    secrets = dict(AI_SEEDS_ADDRESS=config['wallet_address'], BINANCE_API_KEY='synthetic',
                   BINANCE_SECRET_KEY='synthetic')
    with patch.object(service, 'open_store', return_value=store), \
            patch('larp.runtime.credentials.runtime_secrets', return_value=secrets), \
            patch.object(service, 'build_driver', return_value=CycleRecorder()):
        raise SystemExit(service.main(['run', '--config', config_path, '--manifest', manifest, '--root', root]))
