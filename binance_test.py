import os
import hmac
import hashlib
import base64
import requests

from datetime import datetime, timezone
from urllib.parse import quote
from dotenv import load_dotenv


# --------------------------------------------------
# Load API credentials
# --------------------------------------------------

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")

if not api_key:
    raise ValueError("BINANCE_API_KEY not found in .env")

if not secret_key:
    raise ValueError("BINANCE_SECRET_KEY not found in .env")


# --------------------------------------------------
# Binance configuration
# --------------------------------------------------

BASE_URL = "https://web3.binance.com/build"
BUILD_PREFIX = "/build"


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

    # BASE_URL already contains /build
    url = BASE_URL + full_path

    print("Timestamp:", timestamp)
    print("Request URL:", url)
    print("Signed path:", request_path)
    print("Signature:", signature)

    response = requests.get(
        url,
        headers=headers,
        timeout=10,
    )

    return response


# --------------------------------------------------
# Sample request
#
# This is the endpoint Binance uses in its
# authentication documentation example.
# --------------------------------------------------

response = binance_get(
    "/api/v1/dex/aggregator/supported/chain",
    {
        "binanceChainId": "56"
    },
)

print("\nStatus code:", response.status_code)

try:
    print("Response:", response.json())
except ValueError:
    print("Response:", response.text)