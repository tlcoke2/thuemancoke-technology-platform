"""Read-only public staging gateway security preflight.

Only GET /health and /ready at a specific Railway staging origin. Never sends
credentials, cookies, signed R2 URLs, API keys, auth codes, patient or CRM data.
This checks externally observable gates, not private Railway configuration.
"""
import argparse
import json
import re
import ssl
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed_origin(origin):
    if not isinstance(origin, str):
        return False
    try:
        value = urlsplit(origin)
        return (value.scheme == "https" and value.hostname is not None
                and value.hostname.endswith("-staging.up.railway.app")
                and value.hostname.startswith("tcl-customer-gateway-staging")
                and not any((value.port, value.path, value.query, value.fragment,
                             value.username, value.password)))
    except ValueError:
        return False


def fetch(origin, path, opener=None):
    if path not in ("/health", "/ready") or not allowed_origin(origin):
        raise ValueError("Only the exact TCL Railway staging HTTPS origin and public probes are allowed")
    opener = opener or build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    response = opener.open(Request(origin + path,
        headers={"Accept": "application/json", "Cache-Control": "no-store"},
        method="GET"), timeout=8)
    with response:
        status = response.getcode()
        headers = {key.lower(): value for key, value in response.headers.items()}
        if status != 200:
            raise ValueError("Probe did not return 200")
        if "application/json" not in headers.get("content-type", "").lower():
            raise ValueError("Probe did not return JSON")
        raw = response.read(4097)
        if len(raw) > 4096:
            raise ValueError("Probe body exceeds maximum")
        return json.loads(raw.decode("utf-8")), headers


def assess(origin, fetcher=fetch):
    """Return (accepted, issues). Never return private probe data."""
    issues = []
    if not allowed_origin(origin):
        return False, ["Origin is not the exact expected TCL staging Railway host"]
    for path in ("/health", "/ready"):
        try:
            obj, headers = fetcher(origin, path)
            if not isinstance(obj, dict):
                raise ValueError("Invalid public probe data")
            if "no-store" not in headers.get("cache-control", ""):
                issues.append(path + ": Cache-Control must prohibit storage")
            if headers.get("x-frame-options", "").upper() != "DENY":
                issues.append(path + ": X-Frame-Options DENY missing")
            if headers.get("x-content-type-options", "").lower() != "nosniff":
                issues.append(path + ": nosniff missing")
            if "max-age=" not in headers.get("strict-transport-security", "").lower():
                issues.append(path + ": HSTS missing")
            csp = headers.get("content-security-policy", "").lower()
            if "frame-ancestors 'none'" not in csp or "default-src 'none'" not in csp:
                issues.append(path + ": restrictive CSP missing")
            if path == "/health":
                for key, expected in (
                    ("ok", True), ("environment", "staging"),
                    ("service", "tcl-customer-gateway"),
                    ("downloadsEnabled", False),
                    ("mfaStepUpEnabled", True),
                    ("authenticatorSetupAvailable", False),
                ):
                    if type(obj.get(key)) is not type(expected) or obj.get(key) != expected:
                        issues.append("/health: unexpected or unsafe " + key)
            elif obj.get("ready") is not True:
                issues.append("/ready: dedicated gateway database not ready")
        except (ValueError, UnicodeError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            issues.append(path + ": unreachable or invalid HTTPS JSON probe")
    return not issues, issues


def main(argv=None):
    cli = argparse.ArgumentParser(description="Public read-only staging gateway readiness check; no authentication")
    cli.add_argument("--origin", required=True, help="TCL Railway staging HTTPS origin only")
    args = cli.parse_args(argv)
    passed, reasons = assess(args.origin)
    if not passed:
        print("PENDING/FAIL: Public staging preflight did not meet secure readiness policy.")
        for reason in reasons:
            print("- " + reason)
        print("This check made no writes and did not request private data.")
        return 1
    print("PASS: Public staging HTTPS probes, response headers and fail-closed settings.")
    print("Downloads disabled, authenticator enrollment closed, MFA enabled, DB ready.")
    print("LIMITATION: No private provider, R2 IAM, database or entitlement assurance was performed.")
    print("No production authorisation is granted by this public preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
