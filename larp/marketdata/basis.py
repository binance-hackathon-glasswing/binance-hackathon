"""Token basis check for live market observations (IDEA-086 BV1-BV4).

`basis_verified` means: the token, its underlying-market row and its price row name the same bStock contract on chain
56; its underlying ticker is the one this run pinned for that token; its token-to-share ratio is a plausible dividend
multiplier that never moves backwards; and its marks agree with each other. It does NOT verify the token against an
independent share price: the kit's sources have none (GAP-22). Executable prices are bounded later, by the planner's
entry-cost cap and the executor's re-quote.
"""
from decimal import Decimal, InvalidOperation, localcontext
import threading

from .port import TOKENS

RATIO_MIN, RATIO_MAX = Decimal(1), Decimal('1.05')
MAX_RATIO_STEP = Decimal('0.01')     # at most +1% from the last accepted ratio
MARK_BPS = Decimal(1)                # tokenPrice against referencePrice x ratio, same response
ENDPOINT_BPS = Decimal(25)           # rwa/price per-share price x ratio against tokenPrice, seconds apart


def _decimal(value):
    """A finite positive decimal from a JSON string, else None."""
    if type(value) is not str or not value.strip():
        return None
    try:
        n = Decimal(value)
    except InvalidOperation:
        return None
    return n if n.is_finite() and n > 0 else None


def _bps(a, b):
    return abs(a - b) / b * 10000


class BasisVerifier:
    """Callable for `MarketPort(basis_verifier=...)`: (symbol, token row, underlying row, price row) ->
    (verified, reason codes, accepted ratio or None). Keeps the last accepted ratio per token for this process."""

    def __init__(self, expected_underlying):
        if (type(expected_underlying) is not dict or not expected_underlying
                or any(s not in TOKENS or type(t) is not str or not t for s, t in expected_underlying.items())):
            raise ValueError('Basis check needs a token -> underlying ticker map for known tokens')
        self.expected = dict(expected_underlying)
        self.accepted = {}
        self._lock = threading.Lock()

    def __call__(self, symbol, row, underlying, price_row):
        reasons = []
        token = TOKENS.get(symbol)
        same = lambda r: str((r or {}).get('tokenContractAddress', '')).lower() == token
        if (token is None or not (same(row) and same(underlying) and same(price_row))
                or row.get('tokenSymbol') != symbol
                or str(row.get('binanceChainId')) != '56' or str(underlying.get('binanceChainId', '56')) != '56'
                or row.get('platformId') != 'bstock' or underlying.get('platformId') != 'bstock'
                or row.get('assetType') is None or row.get('assetType') != underlying.get('assetType')):
            reasons.append('BV1_IDENTITY')
        if self.expected.get(symbol) is None or row.get('underlyingTicker') != self.expected[symbol]:
            reasons.append('BV2_UNDERLYING')
        ratio = _decimal(row.get('tokenToShareRatio'))
        if ratio is None:
            reasons.append('BV3_RATIO_MISSING')
        elif not RATIO_MIN <= ratio <= RATIO_MAX:
            reasons.append('BV3_RATIO_RANGE')
            ratio = None
        mark, reference, per_share = (_decimal(row.get('tokenPrice')), _decimal(row.get('referencePrice')),
                                      _decimal((price_row or {}).get('tokenPrice')))
        if None in (mark, reference, per_share):
            reasons.append('BV4_PRICE_MISSING')
        elif ratio is not None:
            with localcontext() as context:
                context.prec = 60
                if _bps(reference * ratio, mark) > MARK_BPS:
                    reasons.append('BV4_MARK')
                if _bps(per_share * ratio, mark) > ENDPOINT_BPS:
                    reasons.append('BV4_ENDPOINT')
        with self._lock:
            last = self.accepted.get(symbol)
            if ratio is not None and last is not None:
                if ratio < last:
                    reasons.append('BV3_RATIO_DECREASED')
                elif ratio > last * (1 + MAX_RATIO_STEP):
                    reasons.append('BV3_RATIO_STEP')
            if not reasons:
                self.accepted[symbol] = ratio
        return not reasons, reasons, ratio
