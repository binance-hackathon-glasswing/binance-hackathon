"""NT-Q1: bounded read-only production native-receipt qualification; never enables it.

Private inputs: NativeRpcQualificationInputs.v1 (providers, tx_hash, wallet).
Only transaction-local prestate proof on a successful finalized native credit can
pass. The resulting report is not provider selection, hosting or top-up approval.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from larp.contracts import ContractError  # noqa: E402
from larp.execution import Blocked, DependencyUnavailable  # noqa: E402
from larp.execution_live.chain import ChainEvidence, Rpc, hash_value, quantity  # noqa: E402
from larp.marketdata.web3 import Artifacts, encoded, utc  # noqa: E402
from larp.sources.live import Refused, git_state, require_committed  # noqa: E402
from tools.deploy.qualify_balance_rpc import (TransportDiagnostics, new_output, providers_from, write_new)  # noqa: E402

CALL_LIMIT = 16
ERRORS = (Blocked, DependencyUnavailable, ContractError, KeyError, TypeError, ValueError, AttributeError, OSError)


def validate_inputs(value):
    keys = {'schema', 'providers', 'tx_hash', 'wallet'}
    if type(value) is not dict or set(value) != keys or value['schema'] != 'NativeRpcQualificationInputs.v1':
        raise ContractError('Exact native qualification inputs required')
    if type(value['wallet']) is not str or not re.fullmatch(r'0x[0-9a-f]{40}', value['wallet']):
        raise ContractError('Expected lowercase public wallet')
    if hash_value(value['tx_hash']) != value['tx_hash']:
        raise ContractError('Expected lowercase public transaction hash')
    providers = providers_from({'balance_rpc_providers': value['providers']})
    return dict(providers=providers, wallet=value['wallet'], tx_hash=value['tx_hash'])


def load_inputs(path):
    path = Path(path)
    if (path.is_symlink() or not path.is_file() or path.stat().st_size > 65536
            or path.resolve().is_relative_to(ROOT) or path.absolute().is_relative_to(ROOT)
            or os.name == 'posix' and path.stat().st_mode & 0o077):
        raise ContractError('Private inputs must be outside the repository with private permissions')
    return validate_inputs(json.loads(path.read_bytes()))


class BudgetRpc:
    def __init__(self, rpc):
        self.rpc, self.calls, self.last_method = rpc, 0, None
        self.native_trace, self.source_id = True, rpc.source_id

    def call(self, method, params):
        if self.calls >= CALL_LIMIT:
            raise Blocked('native qualification read budget exhausted')
        self.calls += 1
        self.last_method = method
        return self.rpc.call(method, params)


def native_credit(proof, expected):
    """Wallet-bound successful net native inflow, excluding actual gas; not a whole-block delta."""
    tx, receipt, native = proof['tx'], proof['receipt'], proof['native_balance']
    if (proof.get('finality_verified') is not True or quantity(receipt['status']) != 1
            or str(tx['from']).lower() != expected['wallet']
            or native['wallet'] != expected['wallet'] or native['tx_hash'] != expected['tx_hash']
            or native['block_hash'] != proof['block_hash'] or quantity(tx['value']) != 0):
        raise Blocked('expected successful wallet-native credit proof required')
    gas = quantity(receipt['gasUsed']) * quantity(receipt.get('effectiveGasPrice', tx['gasPrice']))
    flow = native['after_wei'] - native['before_wei'] + gas
    if type(flow) is not int or flow <= 0:
        raise Blocked('positive transaction-native credit required')
    return flow, gas


def probe(inputs, output, *, build_id, rpc_factory=Rpc):
    inputs = validate_inputs(dict(schema='NativeRpcQualificationInputs.v1', **inputs))
    if not re.fullmatch(r'[0-9a-f]{40}', build_id):
        raise ContractError('Full source commit required')
    report = dict(schema='NativeRpcQualification.v1', build_id=build_id, checked_at=utc(),
                  wallet=inputs['wallet'], tx_hash=inputs['tx_hash'], chain_id=56,
                  scope='EXACT_TRANSACTION_PROOF_ONLY', signing_enabled=False, runtime_enabled=False,
                  providers_selected=False, hosted_check='NOT_RUN', agent_topup_round='NOT_RUN', results=[])
    for provider in inputs['providers']:
        directory = output / provider['source_id']
        artifacts = Artifacts(directory)
        row = dict(source_id=provider['source_id'], status='INCONCLUSIVE', reason='RPC_OR_NATIVE_EVIDENCE_REFUSED')
        budget = diagnostics = None
        try:
            rpc = rpc_factory(provider['url'], artifacts=artifacts, source_id=provider['source_id'], native_trace=True)
            diagnostics = TransportDiagnostics(rpc.opener)
            rpc.opener = diagnostics
            budget = BudgetRpc(rpc)
            proof = ChainEvidence(budget).native_receipt(inputs['tx_hash'])
            flow, gas = native_credit(proof, inputs)
            proof_sha = artifacts.put(proof)
            row.update(status='PASS_TRANSACTION_EVIDENCE', reason=None, proof_sha256=proof_sha,
                       block_number=proof['block_number'], block_hash=proof['block_hash'],
                       finalized_height=proof['finalized_height'], trace_sha256=proof['native_balance']['trace_sha256'],
                       net_native_inflow_excluding_gas_wei=str(flow), actual_gas_wei=str(gas))
        except ERRORS:
            if diagnostics and diagnostics.reason:
                row['reason'] = diagnostics.reason
        row.update(rpc_calls=budget.calls if budget else 0,
                   last_method=budget.last_method if budget else None,
                   http_status=diagnostics.http_status if diagnostics else None,
                   observation_hashes=sorted(p.stem for p in directory.glob('*.json')
                                              if re.fullmatch(r'[0-9a-f]{64}', p.stem)))
        report['results'].append(row)
    report['all_transaction_proofs_passed'] = all(r['status'] == 'PASS_TRANSACTION_EVIDENCE' for r in report['results'])
    write_new(output / 'report.json', encoded(report) + b'\n')
    return report


def main(argv=None, *, state=None, rpc_factory=Rpc):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        current = git_state() if state is None else state
        require_committed(current, False)
        inputs = load_inputs(args.inputs)
        output = new_output(args.out)
        report = probe(inputs, output, build_id=current['commit'], rpc_factory=rpc_factory)
        print(json.dumps(report, sort_keys=True))
        return 0 if report['all_transaction_proofs_passed'] else 2
    except (Refused, *ERRORS):
        print(json.dumps(dict(status='NATIVE_QUALIFICATION_REFUSED', signing_enabled=False, runtime_enabled=False)))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
