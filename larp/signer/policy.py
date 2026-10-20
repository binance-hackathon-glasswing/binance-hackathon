"""The signer's own signing policy (WR02, issue #44; IDEA-049-C WR-C).

The signer host exists so that a compromised primary cannot spend the wallet. `validate_payload` checks a payload
against the intent, but primary writes the intent, so those checks only prove that its request is self-consistent.
This policy is read from the signer's root-owned configuration (`/etc/larp/signer.json`, `signing_policy`), which the
release manifest pins (`verify_service_config`); no database role can change it. Every request is checked against it
before the key is used:

- the intent's tokens and router, an approve's token and spender, and a swap's router and decoded tokens are in the
  signer's own lists;
- an approve's amount and a swap's decoded input are at most the per-token cap, and an unlimited approve is refused;
- the transaction fee limit (`gas * gas_price`) is at most the fee cap;
- a swap pays out to the signer's wallet and sends no native value. With the untrusted-router decoder the recipient
  is not in the calldata; that mode is chosen by the signer's own pinned config (IDEA-070 B02-U, DEV-23).

Cap values are a team decision (IDEA-049-C WR-C); `cap_basis` labels where they come from. Both dev and live
service configurations refuse the pending-decision example marker (IDEA-070 SR-01).
"""
from dataclasses import dataclass
import re

from larp.contracts import ContractError
from larp.execution import BSTOCKS, NATIVE_BNB, USDT, Blocked, REVOKE_TOKENS

EXAMPLE_CAP_BASIS = 'EXAMPLE_PENDING_TEAM_DECISION'
UNIVERSE = frozenset({USDT, NATIVE_BNB}) | BSTOCKS
UNLIMITED = 2**255  # an approve this large is unlimited whatever the cap
MAX_CAP = 2**128
KEYS = frozenset({'cap_basis', 'allowed_spenders', 'allowed_tokens', 'max_input_units', 'max_fee_wei'})
_ADDRESS = re.compile(r'0x[0-9a-f]{40}')
_UNITS = re.compile(r'[1-9][0-9]{0,38}')


def _addresses(value, what):
    if type(value) is not list or not value or any(type(a) is not str or not _ADDRESS.fullmatch(a) for a in value):
        raise ContractError('signing_policy.' + what + ' must list lowercase addresses')
    if len(set(value)) != len(value):
        raise ContractError('signing_policy.' + what + ' repeats an address')
    return frozenset(value)


def _units(value, what):
    # Decimal strings: JSON numbers above 2**53 lose precision in common tools.
    if type(value) is not str or not _UNITS.fullmatch(value) or int(value) >= MAX_CAP:
        raise ContractError('signing_policy.' + what + ' must be a positive decimal string below 2**128')
    return int(value)


@dataclass(frozen=True)
class SigningPolicy:
    cap_basis: str
    allowed_spenders: frozenset
    allowed_tokens: frozenset
    max_input_units: dict
    max_fee_wei: int
    allowance_recovery: bool = False

    @classmethod
    def from_config(cls, value):
        if type(value) is not dict or set(value) - {'allowance_recovery'} != KEYS:
            raise ContractError('signing_policy needs exactly: ' + ','.join(sorted(KEYS)))
        if type(value.get('allowance_recovery', False)) is not bool:
            raise ContractError('signing_policy.allowance_recovery must be an explicit boolean')
        if type(value['cap_basis']) is not str or not value['cap_basis'].strip():
            raise ContractError('signing_policy.cap_basis must name where the caps come from')
        spenders = _addresses(value['allowed_spenders'], 'allowed_spenders')
        tokens = _addresses(value['allowed_tokens'], 'allowed_tokens')
        if not tokens <= UNIVERSE:
            raise ContractError('signing_policy.allowed_tokens must be USDT, eligible bStocks or native BNB')
        if spenders & UNIVERSE:
            raise ContractError('signing_policy.allowed_spenders cannot name a token')
        caps = value['max_input_units']
        if type(caps) is not dict or set(caps) != tokens - {NATIVE_BNB}:
            raise ContractError('signing_policy.max_input_units must cap exactly each allowed payable token')
        return cls(value['cap_basis'], spenders, tokens,
                   {token: _units(cap, 'max_input_units') for token, cap in caps.items()},
                   _units(value['max_fee_wei'], 'max_fee_wei'), value.get('allowance_recovery', False))

    def _input(self, token, amount):
        if token not in self.max_input_units:
            raise Blocked('signer policy: token not allowed')
        if type(amount) is not int or amount >= UNLIMITED:
            raise Blocked('signer policy: unlimited amount refused')
        if not 0 < amount <= self.max_input_units[token]:
            raise Blocked('signer policy: amount exceeds signer input cap')

    def check(self, intent, step, payload, decoder, wallet):
        """Raises Blocked unless this request is inside the signer's own policy. Called before any key use."""
        if intent.pay_token not in self.allowed_tokens or intent.receive_token not in self.allowed_tokens:
            raise Blocked('signer policy: intent token not allowed')
        if intent.router not in self.allowed_spenders:
            raise Blocked('signer policy: intent spender not allowed')
        if payload.sender != wallet or payload.value != 0:
            raise Blocked('signer policy: sender or native value refused')
        if payload.gas * payload.gas_price > self.max_fee_wei:
            raise Blocked('signer policy: transaction fee exceeds signer fee cap')
        if step == 'APPROVE' or step in REVOKE_TOKENS:
            data = payload.data
            if (payload.to not in self.allowed_tokens or type(data) is not str
                    or not re.fullmatch(r'0x095ea7b3[0-9a-fA-F]{128}', data) or data[10:34] != '0' * 24):
                raise Blocked('signer policy: approve token or shape not allowed')
            if '0x' + data[34:74].lower() not in self.allowed_spenders:
                raise Blocked('signer policy: approve spender not allowed')
            if step in REVOKE_TOKENS:
                if (not self.allowance_recovery or getattr(decoder, 'mode', None) != 'untrusted'
                        or getattr(decoder, 'router', None) != intent.router or intent.kind != 'BSTOCK_TRADE'
                        or payload.to != REVOKE_TOKENS[step] or int(data[74:], 16) != 0
                        or '0x' + data[34:74].lower() != intent.router):
                    raise Blocked('signer policy: zero-only allowance recovery not authorized')
            else:
                self._input(payload.to, int(data[74:], 16))
        elif step == 'SWAP':
            if payload.to not in self.allowed_spenders:
                raise Blocked('signer policy: swap spender not allowed')
            economics = decoder.decode(payload)  # GAP-29: UnverifiedRouter refuses every swap here
            if economics.receive_token not in self.allowed_tokens:
                raise Blocked('signer policy: swap token not allowed')
            # The untrusted-router mode comes from the signer's own pinned policy, never from the request (B02-U).
            unverified = economics.recipient is None and getattr(decoder, 'mode', None) == 'untrusted'
            if (economics.recipient != wallet and not unverified) or economics.native_value != 0:
                raise Blocked('signer policy: swap recipient or native value refused')
            self._input(economics.pay_token, economics.amount)
        else:
            raise Blocked('signer policy: unsupported transaction step')
