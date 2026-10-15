import os
import sys
import hmac
import hashlib
import base64
import requests

from datetime import datetime, timezone
from urllib.parse import quote
from dotenv import load_dotenv
from tools.probe_http import envelope


# --------------------------------------------------
# Load API credentials
# --------------------------------------------------

api_key = None
secret_key = None


# --------------------------------------------------
# Binance configuration
# --------------------------------------------------

BASE_URL = "https://web3.binance.com/build"
BUILD_PREFIX = "/build"

# Optional X-OC-RECV-WINDOW (allowed clock skew in ms; server default 5000, max 60000).
# Set e.g. BINANCE_RECV_WINDOW=15000 (the kit's Python demo value); unset = header not sent.
RECV_WINDOW = None


# --------------------------------------------------
# Helper: generate ISO 8601 UTC timestamp
# Example: 2026-10-03T01:25:14.103Z
# --------------------------------------------------

def get_timestamp():
    now = datetime.now(timezone.utc)

    return (
        now.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{now.microsecond // 1000:03d}Z"
    )


# --------------------------------------------------
# Helper: create query string
#
# Binance specifically requires the EXACT encoded
# query string used in the request to also be signed.
#
# quote() gives spaces as %20 rather than +
# --------------------------------------------------

def encode_params(params):
    return "&".join(
        f"{quote(str(key), safe='')}={quote(str(value), safe='')}"
        for key, value in params.items()
    )


# --------------------------------------------------
# Authenticated Binance GET request
# --------------------------------------------------

def binance_get(path, params=None):
    params = params or {}

    # Build query string
    query_string = encode_params(params)

    if query_string:
        full_path = f"{path}?{query_string}"
    else:
        full_path = path

    # IMPORTANT:
    # The path used for signing MUST include /build
    request_path = BUILD_PREFIX + full_path

    timestamp = get_timestamp()
    method = "GET"
    body = ""

    # Binance signing format:
    #
    # timestamp + method + requestPath + body
    #
    pre_hash = (
        timestamp
        + method
        + request_path
        + body
    )

    signature = base64.b64encode(
        hmac.new(
            secret_key.encode("utf-8"),
            pre_hash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    # Required Binance headers
    headers = {
        "X-OC-APIKEY": api_key,
        "X-OC-TIMESTAMP": timestamp,
        "X-OC-SIGN": signature,
    }
    if RECV_WINDOW:
        headers["X-OC-RECV-WINDOW"] = RECV_WINDOW

    # BASE_URL already contains /build
    url = BASE_URL + full_path

    print("Timestamp:", timestamp)
    print("Request URL:", url)
    print("Signed path:", request_path)

    response = requests.get(
        url,
        headers=headers,
        timeout=10,
        allow_redirects=False,
    )

    return response.status_code, envelope(response, (api_key, secret_key, signature))


# --------------------------------------------------
# Sample request
#
# This is the endpoint Binance uses in its
# authentication documentation example.
# --------------------------------------------------

def main():
    global api_key, secret_key, RECV_WINDOW
    load_dotenv()
    api_key, secret_key = os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY")
    RECV_WINDOW = os.getenv("BINANCE_RECV_WINDOW")
    if not api_key or not secret_key:
        print("BINANCE_API_KEY / BINANCE_SECRET_KEY not found in .env")
        return 1
    try:
        status, body = binance_get(
            "/api/v1/dex/aggregator/supported/chain",
            {"binanceChainId": "56"},
        )
    except requests.RequestException:
        print("Request failed: network error")
        return 1

    print("\nStatus code:", status)

    print("Response:", body)

    # Only code == 0 means success; HTTP 200 can still carry an error code
    # (SKILL.md F-94, F-108; participant-kit.md K7).
    if status != 200 or type(body.get("code")) is not int or body["code"] != 0:
        code = body.get("code") if isinstance(body, dict) else None
        print("FAILED: code =", code)
        return 1

    print("OK: code == 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
