"""Sanitized response boundary shared by the read-only signed probes."""

from tools.w08_capabilities import ProbeStopped, classify, scrub


def envelope(response, secrets):
    """Return only sanitized JSON, and never promote malformed/HTTP errors to code 0."""
    try:
        body = scrub(response.json(), secrets)
    except (ValueError, UnicodeError, RecursionError):
        return {"code": None, "msg": f"HTTP {response.status_code}, invalid JSON", "data": None}
    if not isinstance(body, dict) or type(body.get("code")) is not int:
        return {"code": None, "msg": "invalid API envelope", "data": None}
    if body["code"] == 0 and response.status_code != 200:
        return {"code": None, "msg": f"HTTP {response.status_code} rejected", "data": None}
    return body


def stop_if_refused(status, body):
    outcome = classify(status, body)
    if outcome in {"authentication_error", "compliance_restriction", "rate_limited",
                   "http_forbidden_unclassified"}:
        raise ProbeStopped(outcome)
