"""Quote proof for the UNTRUSTED router path (IDEA-088, SJ-11-QV01; IDEA-070 B02-U, DEV-23).

`MarketPort.observe` calls `UntrustedQuoteVerifier(raw, request, observation)` with a quote-and-swap response. It
returns the proof `MarketPort._executable_quote` binds to the quote, or raises `Unavailable`; there is no partial
proof. The checks:

- the response is a plain LiquidMesh SWAP built for this wallet at the requested slippage, with no explicit fee whose
  denomination is unproved (fees are taken as included in the quoted amounts, as the profile's `fee_bps = 0`, #119);
- the transaction decodes with the signer's own `UntrustedRouterDecoder` (byte-exact layout; the recipient is not in
  the calldata, so it stays unverified, as the signer and execution accept only in this mode);
- the minimum output is inside the slippage limit and the inner deadline is after the response arrived;
- at one numeric block the router dispatches the swap selector to the pinned facet and both code hashes match.
  Other-token allowances refuse by default; an explicit recovery opt-in records them for executor cleanup.

Gas: a swap cannot be estimated before its approve (IDEA-070 KG-DEC-01-H P3), so no exact estimate exists when the
plan is made. The proof reserves the profile's `gas_action_budget_units`, which bounds every fee execution can
authorize for one intent (`gas_budget` <= action budget, CAP-02), and gives `gas_sizing_budget_units` (LD09-B, the
expected fee) for the planner's cost check. Its `gas_basis` says so; nothing is labelled exact.
"""
from datetime import datetime
from types import SimpleNamespace
import re

from larp.contracts import ContractError
from larp.execution import Blocked, DependencyUnavailable, Payload
from .port import integer, number, slippage_percent
from .web3 import Unavailable, single

GAS_BASIS = 'EXECUTION_FEE_AUTHORITY'
FEE_BASIS = 'ROUTE_FEES_IN_QUOTED_AMOUNTS'
ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}')


class ProviderRpc:
    """The runtime's balance RPC providers as one read RPC for the router preflight. Each call goes to the first
    provider that answers; only unavailability moves on, so a refused or malformed answer still fails closed."""
    mode = 'live'

    def __init__(self, providers):
        self.providers = list(providers)
        if not self.providers:
            raise ContractError('The router preflight needs at least one RPC provider')

    def call(self, method, params):
        for rpc in self.providers:
            try:
                return rpc.call(method, params)
            except DependencyUnavailable:
                continue
        raise DependencyUnavailable('every RPC provider is unavailable')


class UntrustedQuoteVerifier:
    def __init__(self, decoder, profile, *, wallet, bnb_decimals, allowance_recovery=False):
        from larp.strategy.schema import initial_gas_only
        if getattr(decoder, 'mode', None) != 'untrusted' or getattr(decoder, 'rpc', None) is None:
            raise ContractError('The quote verifier needs an untrusted-router decoder bound to a read RPC')
        if type(wallet) is not str or not ADDRESS.fullmatch(wallet):
            raise ContractError('The quote verifier needs the public wallet address')
        try:
            initial = initial_gas_only(profile)
            action, sizing = profile['gas_action_budget_units'], profile['gas_sizing_budget_units']
            scale = profile['quote_cost_summary']['bnb_decimals']
            slippage = profile['slippage_bps']
            cleanup_sizing = max((r['approve_gas_bnb_units'] * 5 + 3) // 4
                                 for r in profile['quote_cost_summary']['symbols'].values())
        except (KeyError, TypeError, AttributeError, ValueError, ContractError):
            raise ContractError('The quote verifier needs an initial-gas-only profile with both gas budgets') from None
        if initial is not True or any(type(v) is not int or v <= 0 for v in (action, sizing)) or sizing > action:
            raise ContractError('The quote verifier needs an initial-gas-only profile with both gas budgets')
        if type(bnb_decimals) is not int or scale != bnb_decimals:
            raise ContractError('Profile gas budgets and the ledger use different BNB scales')
        self.decoder, self.wallet = decoder, wallet.lower()
        self.action, self.sizing = action, sizing
        self.slippage_bps, self.slippage = slippage, slippage_percent(slippage)
        self.cleanup_sizing = cleanup_sizing
        if type(allowance_recovery) is not bool:
            raise ContractError('allowance_recovery must be an explicit boolean')
        self.allowance_recovery = allowance_recovery

    def __call__(self, raw, request, observation):
        try:
            return self._proof(raw)
        except Blocked as error:  # DependencyUnavailable included: an unreachable RPC proves nothing
            raise Unavailable('quote proof refused: ' + str(error)) from None
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            raise Unavailable('quote proof schema rejected') from None

    def _proof(self, raw):
        q = single(raw)
        rr, tx = q['routerResult'], q['tx']
        if type(raw['artifact_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', raw['artifact_sha256']):
            raise Blocked('quote response has no content hash')
        if q.get('executionMode') != 'SWAP' or q.get('rfq') is not None or rr.get('vendorName') != 'LiquidMesh':
            raise Blocked('quote execution mode or vendor refused')
        if tx.get('from') is not None and str(tx['from']).lower() != self.wallet:
            raise Blocked('quote built for another wallet')
        if tx.get('slippagePercent') is not None and number(tx['slippagePercent']) != number(self.slippage):
            raise Blocked('quote slippage differs from the requested limit')
        if rr.get('feeAmount') not in (None, '') and number(rr['feeAmount']) != 0:
            raise Blocked('explicit route fee has no proved denomination')
        payload = Payload(56, self.wallet, str(tx['to']).lower(), integer(tx['value']), 0, integer(tx['gas']),
                          integer(tx['gasPrice']), tx['data'])  # execution assigns the nonce
        economics = self.decoder.decode(payload)
        received, minimum = integer(rr['toTokenAmount']), economics.minimum_output
        if not 0 < minimum <= received or minimum < received * (10000 - self.slippage_bps) // 10000:
            raise Blocked('quote minimum output is outside the slippage limit')
        available = datetime.fromisoformat(raw['available_at'].replace('Z', '+00:00'))
        if available.tzinfo is None or economics.deadline <= available.timestamp():
            raise Blocked('quote expired at retrieval completion')
        # Live pins always apply. Without recovery, the execution service's own before-approve preflight also
        # requires clean other-token allowances. The decoder comes from the pinned policy, never the response.
        intent = SimpleNamespace(router=self.decoder.router, wallet=self.wallet,
                                 pay_token=economics.pay_token, amount=economics.amount)
        dirty = {}
        if self.allowance_recovery:
            # Numeric-block code/facet pins and all six allowances are still verified. Only execution
            # may clean them; its independent strict preflight remains mandatory before every swap.
            if payload.to != self.decoder.router or payload.value != 0:
                raise Blocked('swap router or native value differs from the pinned router')
            from .port import TOKENS
            symbols = {v: k for k, v in TOKENS.items()} | {
                '0x55d398326f99059ff775485246999027b3197955': 'USDT'}
            dirty = {symbols[t]: a for t, a in self.decoder.allowances(intent).items() if a}
        else:
            try:
                self.decoder.preflight(intent, payload, approved=False)
            except Blocked as error:
                if str(error) == 'router allowance exceeds what this swap may take':
                    from .port import TOKENS
                    symbols = {v: k for k, v in TOKENS.items()}
                    dirty = {symbols.get(t, 'USDT'): a for t, a in self.decoder.allowances(intent).items()
                             if a and t != economics.pay_token}
                    raise Blocked('DIRTY_ROUTER_ALLOWANCE:' + ','.join(sorted(dirty))) from None
                raise
        expected = self.sizing + (sum(s != symbols.get(economics.pay_token, 'USDT') for s in dirty)
                                  * self.cleanup_sizing if self.allowance_recovery else 0)
        if expected > self.action:
            raise Blocked('observed allowance cleanup exceeds action gas budget')
        return dict(source_hash=raw['artifact_sha256'], economics=economics, payload=payload, route_valid=True,
                    gas_basis=GAS_BASIS, gas_bnb_units=self.action, expected_gas_bnb_units=expected,
                    fee_units=0, fee_basis=FEE_BASIS, slippage_bps=self.slippage_bps, dirty_allowances=dirty)
