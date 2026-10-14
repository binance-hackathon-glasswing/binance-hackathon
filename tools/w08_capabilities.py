"""W08 read-only evidence collector. No transaction signer or broadcaster.

See docs/ledger/EXP-005.md for preregistration and docs/engineering/W08.md
for interpretation. Endpoint success is not an execution authorization.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import shlex
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://web3.binance.com/build"
PREFIX = "/api/v1/dex/"
USDT = "0x55d398326f99059ff775485246999027b3197955"
TOKENS = {
    "NVDAB": "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "GOOGLB": "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "SKHYB": "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "TSLAB": "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "MSFTB": "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
}
READS = frozenset({
    ("GET", "aggregator/supported/chain"),
    ("GET", "market/rwa/tokens"),
    ("GET", "market/rwa/underlying-market"),
    ("GET", "aggregator/quote-and-swap"),
    ("GET", "aggregator/approve-transaction"),
    ("POST", "pre-transaction/gas-limit"),
    ("POST", "balance/token-balances-by-address"),
    ("GET", "post-transaction/transactions-by-address"),
    ("GET", "post-transaction/transaction-detail-by-txhash"),
})
ENV_NAMES = ("BINANCE_API_KEY", "BINANCE_SECRET_KEY", "AI_SEEDS_ADDRESS")


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def public_address(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise ValueError("Expected a 20-byte public address")
    return value.lower()


def positive_units(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError("Expected positive integer base units")
    if int(value) >= 2**256:
        raise ValueError("Amount exceeds uint256")
    return value


def selected_env(path=None):
    """Parse only the three named fields; no dotenv expansion or wallet key use."""
    values = {name: os.environ[name] for name in ENV_NAMES if name in os.environ}
    if path:
        with Path(path).open() as stream:
            for line in stream:
                match = re.match(r"^\s*(?:export\s+)?([A-Z_]+)\s*=\s*(.*)$", line)
                if match and match[1] in ENV_NAMES and match[1] not in values:
                    parts = shlex.split(match[2], comments=True)
                    if len(parts) != 1 or "$" in parts[0] or "`" in parts[0]:
                        raise ValueError("Selected env fields must be nonempty literal values")
                    values[match[1]] = parts[0]
    return values


def scrub(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [scrub(item, secrets) for item in value]
    if isinstance(value, dict):
        return {scrub(key, secrets): scrub(item, secrets) for key, item in value.items()}
    return value


def retry_after(value, now):
    try:
        seconds = float(value)
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except (ValueError, TypeError):
        try:
            return max(0.0, parsedate_to_datetime(value).timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            return None


def classify(status, body):
    code = body.get("code") if isinstance(body, dict) else None
    if code == 40304:
        return "compliance_restriction"
    if status == 429 or code == 42900:
        return "rate_limited"
    if code in (40100, 40101, 40102, 40103, 40104) or status == 401:
        return "authentication_error"
    if status == 403:
        return "http_forbidden_unclassified"
    if status == 200 and type(code) is int and code == 0:
        return "ok"
    return "api_or_http_error"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ProbeStopped(RuntimeError):
    def __init__(self, outcome):
        super().__init__(outcome)
        self.outcome = outcome


class ReadClient:
    def __init__(self, api_key, secret, opener=None):
        self.api_key, self.secret = api_key, secret
        self.opener = opener or build_opener(NoRedirect())
        self.records = []

    def request(self, method, endpoint, params):
        if (method, endpoint) not in READS:
            raise ValueError("Endpoint is outside the W08 read-only allowlist")
        target = PREFIX + endpoint
        payload = b""
        if method == "GET":
            target += "?" + urlencode(params)
        else:
            payload = canonical(params).encode()
        timestamp = utc()
        signature = base64.b64encode(hmac.new(
            self.secret.encode(), timestamp.encode() + method.encode()
            + b"/build" + target.encode() + payload, hashlib.sha256,
        ).digest()).decode()
        req = Request(BASE + target, data=payload if method == "POST" else None,
                      method=method, headers={"X-OC-APIKEY": self.api_key,
                      "X-OC-TIMESTAMP": timestamp, "X-OC-SIGN": signature,
                      "Content-Type": "application/json"})
        record = {"method": method, "endpoint": endpoint, "params": params,
                  "requested_utc": timestamp}
        started = time.monotonic()
        try:
            try:
                response = self.opener.open(req, timeout=20)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read(2 * 1024 * 1024 + 1)
                record.update(http_status=response.code,
                              retry_after_seconds=retry_after(response.headers.get("Retry-After"), time.time()),
                              response_sha256=hashlib.sha256(raw).hexdigest())
            if len(raw) > 2 * 1024 * 1024:
                record["outcome"] = "response_too_large"
            else:
                try:
                    body = json.loads(raw)
                    record.update(response=body, outcome=classify(record["http_status"], body))
                except (ValueError, UnicodeError):
                    record["outcome"] = "non_json_response"
        except (URLError, TimeoutError, OSError):
            # Exception strings may include URLs/headers; never persist them.
            record["outcome"] = "transport_error"
        record.update(observed_utc=utc(), elapsed_ms=round((time.monotonic() - started) * 1000))
        record = scrub(record, (self.api_key, self.secret, signature))
        self.records.append(record)
        return record


def one_data(record):
    if record.get("outcome") != "ok":
        return None
    data = record.get("response", {}).get("data")
    if isinstance(data, list):
        data = data[0] if len(data) == 1 else None
    return data if isinstance(data, dict) else None


def inspect_approve(data, expected_spender, expected_amount):
    """Strict ERC20 approve ABI decode only; not a complete W04 authorization."""
    expected_spender = public_address(expected_spender)
    positive_units(expected_amount)
    if not isinstance(data, str) or not re.fullmatch(r"0x095ea7b3[0-9a-fA-F]{128}", data):
        raise ValueError("Unknown or malformed approve calldata")
    spender_word, amount_word = data[10:74], data[74:138]
    if spender_word[:24] != "0" * 24:
        raise ValueError("Noncanonical address padding")
    spender = public_address("0x" + spender_word[24:])
    amount = int(amount_word, 16)
    if spender != expected_spender or amount != int(expected_amount):
        raise ValueError("Approve payload disagrees with requested spender/amount")
    return {"spender": spender, "amount_base_units": str(amount)}


def inspect_quote(record):
    data = one_data(record)
    if not data or not isinstance(data.get("tx"), dict):
        return {"outcome": "missing_or_ambiguous_payload", "signable": False}
    tx = data["tx"]
    calldata = tx.get("data")
    valid = isinstance(calldata, str) and re.fullmatch(r"0x[0-9a-fA-F]{8}(?:[0-9a-fA-F]{2})*", calldata)
    return {"outcome": "unknown_router_abi" if valid else "malformed_calldata",
            "router": tx.get("to"), "selector": calldata[:10] if valid else None,
            "calldata_bytes": (len(calldata) - 2) // 2 if valid else None,
            "execution_mode": data.get("executionMode"),
            "signable": False, "encoded_deadline_verified": False,
            "encoded_minimum_verified": False}


def collect(client, address, symbols, amount, tx_hashes):
    def call(method, endpoint, params):
        if client.records:
            time.sleep(0.35)
        result = client.request(method, endpoint, params)
        if result["outcome"] in {"compliance_restriction", "authentication_error", "rate_limited",
                                 "http_forbidden_unclassified"}:
            raise ProbeStopped(result["outcome"])
        return result

    connectivity = call("GET", "aggregator/supported/chain", {"binanceChainId": "56"})
    if connectivity["outcome"] != "ok":
        return {"blocked": connectivity["outcome"], "routes": []}
    call("GET", "market/rwa/tokens", {"binanceChainId": "56", "platformId": "bstock"})
    if address is None:
        return {"blocked": "wallet_observations_not_requested", "routes": []}
    call("POST", "balance/token-balances-by-address", {"address": address,
         "tokenContractAddresses": [{"binanceChainId": "56", "tokenContractAddress": token}
                                    for token in ["", USDT, *TOKENS.values()]]})
    call("GET", "post-transaction/transactions-by-address", {"address": address, "chains": "56", "limit": "100"})
    for tx_hash in tx_hashes:
        call("GET", "post-transaction/transaction-detail-by-txhash", {"binanceChainId": "56", "txHash": tx_hash})
    routes = []
    for symbol in symbols:
        call("GET", "market/rwa/underlying-market", {"binanceChainId": "56", "tokenContractAddress": TOKENS[symbol]})
        legs = [(USDT, TOKENS[symbol], amount, "buy")]
        for pay, receive, units, direction in legs:
            quote = call("GET", "aggregator/quote-and-swap", {"binanceChainId": "56",
                         "amount": units, "fromTokenAddress": pay, "toTokenAddress": receive,
                         "userWalletAddress": address, "vendor": "LiquidMesh", "slippagePercent": "0.5"})
            inspection = inspect_quote(quote)
            routes.append({"symbol": symbol, "direction": direction, **inspection})
            data = one_data(quote)
            if not data or not isinstance(data.get("routerResult"), dict) or not isinstance(data.get("tx"), dict):
                continue
            rr, tx = data["routerResult"], data["tx"]
            if direction == "buy":
                try:
                    sell_amount = positive_units(rr.get("toTokenAmount"))
                    legs.append((receive, pay, sell_amount, "sell"))
                except ValueError:
                    pass
            try:
                router = public_address(tx.get("to"))
                if not isinstance(rr.get("vendorName"), str) or not rr["vendorName"]:
                    continue
                approve = call("GET", "aggregator/approve-transaction", {"binanceChainId": "56",
                               "tokenContractAddress": pay, "approveAmount": units, "vendor": rr["vendorName"]})
                approval = one_data(approve)
                if approval:
                    if public_address(approval.get("dexContractAddress")) != router:
                        raise ValueError("Spender and router differ")
                    routes[-1]["approve_decode"] = inspect_approve(approval.get("data"), router, units)
                else:
                    routes[-1]["approve_decode"] = "unavailable"
            except ValueError:
                routes[-1]["approve_decode"] = "mismatch_or_malformed"
            # Gas simulation receives precisely the returned unsigned payload; never broadcast.
            if inspection["outcome"] == "unknown_router_abi":
                try:
                    public_address(tx.get("to"))
                    value = str(tx.get("value"))
                    if not re.fullmatch(r"0|[1-9][0-9]*", value):
                        raise ValueError("Invalid value")
                    gas = call("POST", "pre-transaction/gas-limit", {"binanceChainId": "56",
                               "evmTx": {"from": address, "to": tx["to"], "data": tx["data"], "value": value}})
                    estimate = one_data(gas)
                    routes[-1]["gas_estimate"] = estimate.get("gasLimit") if estimate else None
                    routes[-1]["gas_outcome"] = gas["outcome"]
                except ValueError:
                    routes[-1]["gas_outcome"] = "malformed_payload"
    return {"routes": routes, "nonce_consumption_proved": False, "finality_proved": False,
            "quote_expiry_proved": False, "replacement_enabled": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--address")
    parser.add_argument("--connectivity-only", action="store_true",
                        help="Probe authentication and token metadata without a wallet")
    parser.add_argument("--symbols", nargs="+", choices=list(TOKENS), default=list(TOKENS))
    parser.add_argument("--amount-base-units", default="1000000000000000000", type=positive_units)
    parser.add_argument("--tx-hash", action="append", default=[])
    args = parser.parse_args()
    try:
        env = selected_env(args.env_file)
        address = None if args.connectivity_only else public_address(args.address or env.get("AI_SEEDS_ADDRESS"))
        if not all(env.get(key) for key in ENV_NAMES[:2]):
            parser.error("BINANCE_API_KEY and BINANCE_SECRET_KEY are required")
        if any(not re.fullmatch(r"0x[0-9a-fA-F]{64}", value) for value in args.tx_hash):
            parser.error("--tx-hash must be a 32-byte public hash")
    except (ValueError, OSError):
        parser.error("Cannot read selected literal credentials/public address")
    client = ReadClient(env[ENV_NAMES[0]], env[ENV_NAMES[1]])
    try:
        summary = collect(client, address, args.symbols, args.amount_base_units, args.tx_hash)
    except ProbeStopped as stopped:
        summary = {"blocked": stopped.outcome, "routes": []}
    report = {"schema": "w08-evidence-v1", "generated_utc": utc(), "chain_id": "56",
              "wallet": address, "summary": summary, "records": client.records}
    content = canonical(report).encode()
    directory = Path("data/w08")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("evidence-" + hashlib.sha256(content).hexdigest() + ".json")
    with path.open("xb") as stream:
        stream.write(content)
    print(canonical({"artifact": str(path), "sha256": hashlib.sha256(content).hexdigest(),
                     "requests": len(client.records), "summary": summary}))


if __name__ == "__main__":
    main()
