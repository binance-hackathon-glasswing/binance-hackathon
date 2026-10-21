"""LD12-M01-RV01: offline reproductions for collector boundaries and timing claims."""
import ast
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from tests.runtime.test_ld12_ops_measure import analyse, FOLDER

PACKET = FOLDER.parents[1] / 'evidence/ld12-ops-measure-20261021/packet.jsonl'


def packet():
    return tuple(json.loads(line) for line in PACKET.read_text().splitlines())


def guarded(host, db):
    source = (FOLDER / 'ops-collect.sh').read_text().split("<<'PY'\n")[3].rsplit('\nPY', 1)[0]
    configs = {'operations.json': dict(host['operations'], database_host='private-db.example'),
               'runtime.json': dict(host['runtime'], wallet_address='0x' + 'ab' * 20,
                                    driver=dict(execution=host['runtime']['execution'], balance_rpc_providers=[dict(url='https://private-rpc.example/token')]))}
    def read_bytes(path):
        return json.dumps(configs[path.name]).encode()
    with patch('pathlib.Path.read_bytes', read_bytes), patch.dict('os.environ',
             HOST_JSON=json.dumps(host), DB_JSON=json.dumps(db)), patch('sys.stdout', new_callable=io.StringIO) as out:
        try:
            exec(compile(source, 'packet_guard', 'exec'), {})
        except SystemExit:
            return False
        return 'packet_gzip_b64' in out.getvalue()


@pytest.mark.parametrize('case', ['activating', 'missing_state', 'runtime_run', 'uploader_run', 'build', 'mode', 'execution'])
def test_retired_trial_guard_refuses_unqualified_state_or_identity(case):
    h, d = packet()
    if case == 'activating': h['units']['larp-runtime']['ActiveState'] = 'activating'
    elif case == 'missing_state': h['units']['larp-runtime'].pop('ActiveState')
    elif case == 'runtime_run': h['runtime']['run_id'] = 'other-run'
    elif case == 'uploader_run': h['uploader']['run_id'] = 'other-run'
    elif case == 'build': h['runtime']['build_id'] = 'f' * 40
    elif case == 'mode': h['runtime']['mode'] = 'live'
    else: h['runtime']['execution'] = 'signed'
    assert not guarded(h, d)


def test_guard_accepts_original_retired_identity_with_safe_boolean_error_flags():
    h, d = packet()
    for row in d['archive']: row[-1] = bool(row[-1])
    assert guarded(h, d)


@pytest.mark.parametrize('private', ['private-rpc.example', 'ab' * 20])
def test_private_host_and_wallet_without_prefix_never_leave_packet(private):
    h, d = packet()
    h['journal']['disk_usage'] = private
    assert not guarded(h, d)


def test_free_form_archive_errors_are_never_exposed():
    h, d = packet()
    d['archive'][0][-1] = 'CredentialPrefixThatWasTruncated'
    assert not guarded(h, d)


def test_failed_host_command_is_not_reported_as_an_empty_success():
    first = (FOLDER / 'ops-collect.sh').read_text().split("<<'PY'\n")[1].split('\nPY', 1)[0]
    node = next(n for n in ast.parse(first).body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    import subprocess
    ns = dict(subprocess=subprocess)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'host_read', 'exec'), ns)
    with patch('subprocess.run', return_value=SimpleNamespace(returncode=1, stdout='', stderr='private')):
        with pytest.raises(ValueError, match='HOST_READ_FAILED'):
            ns['run']('journalctl', '-k')


def test_delivery_reports_attempt_clock_and_unknown_actual_ack_latency():
    h, d = packet()
    out = analyse.summary(h, d)['delivery']
    assert out['actual_dispatch_to_ack_s'] == 'NOT_MEASURED'
    assert 'upper bound' not in out['note'].lower()
    assert out['dispatch_to_latest_attempt_clock_s']['max'] == 5.387


def test_distinct_events_with_identical_timestamps_do_not_merge():
    rows = [[1000, 0, 1, 32000, 'ACK', '200', True, 1],
            [1000, 0, 1, 34000, 'ACK', '200', True, 2]]
    assert analyse.delivery(rows, 30000, 300000)['logs'] == 2


def test_absent_signer_is_distinct_from_a_failed_host_read():
    first = (FOLDER / 'ops-collect.sh').read_text().split("<<'PY'\n")[1].split('\nPY', 1)[0]
    node = next(n for n in ast.parse(first).body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    import subprocess
    ns = dict(subprocess=subprocess)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'host_read', 'exec'), ns)
    with patch('subprocess.run', return_value=SimpleNamespace(returncode=1,
               stdout='LoadState=not-found\nActiveState=inactive\n', stderr='')):
        assert 'not-found' in ns['run']('systemctl', 'show', 'larp-signer')
        with pytest.raises(ValueError): ns['run']('systemctl', 'show', 'larp-runtime')


from contextlib import contextmanager
from tests.support import DatabaseCase


class CollectorDatabaseChecks(DatabaseCase):
    def test_every_supported_collector_query_parses_on_current_postgres_schema(self):
        import psycopg
        source = (FOLDER / 'ops-collect.sh').read_text().split("<<'PY'\n")[2].split('\nPY', 1)[0]
        queries = [n for n in ast.parse(source).body if isinstance(n, ast.Expr)
                   and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                   and n.value.func.id == 'q']
        assert len(queries) == 12
        for node in queries:
            name, sql = (ast.literal_eval(arg) for arg in node.value.args[:2])
            params = () if any(k.arg == 'params' for k in node.value.keywords) else ('run',)
            if name == 'anchors':
                with pytest.raises(psycopg.errors.UndefinedTable), self.store.transaction() as db:
                    db.execute(sql, params).fetchall()
            else:
                with self.store.transaction() as db:
                    db.execute('SET TRANSACTION READ ONLY')
                    db.execute(sql, params).fetchall()

    def test_collector_transaction_rejects_writes_at_the_database(self):
        import psycopg
        source = (FOLDER / 'ops-collect.sh').read_text().split("<<'PY'\n")[2].split('\nPY', 1)[0]
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'RO')
        store = self.store
        class Base:
            def transaction(self): return store.transaction()
        ns = dict(IamPostgresStore=Base, contextmanager=contextmanager)
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'collector_ro', 'exec'), ns)
        with ns['RO']().transaction() as db:
            assert db.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction), ns['RO']().transaction() as db:
            db.execute("INSERT INTO runs(run_id) VALUES ('refused')")
