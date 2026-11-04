"""Offline staging Gate B operator-evidence validator. No network or DB access.

This validates *redacted, operator-recorded* acceptance evidence, not WorkOS/R2
real-time behavior. A PASS is NOT production authorization. No secret fields.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re


CHECKS = (
    "customer_denied_before_approval",
    "self_approval_denied",
    "separate_mfa_approver",
    "customer_approved",
    "cross_tenant_customer_denied",
    "cross_tenant_membership_hidden",
    "grant_revoked",
    "post_revoke_new_url_denied",
    "old_r2_get_expired",
    "old_gateway_session_denied",
    "new_session_revoked_access_denied",
    "staging_flags_restored",
    "download_did_not_create_license",
    "release_master_untouched",
    "clinical_databases_untouched",
)

TEMPLATE = {
    "schema": "tcl-gateway-stage-b-v1",
    "environment": "staging",
    "service": "tcl-customer-gateway-staging",
    "test_reference": "SYNTHETIC-UAT-REDACTED",
    "git_commit": "",
    "timestamps_utc": {
        "url_issued": None,
        "grant_revoked": None,
        "post_revoke_denial": None,
        "expired_r2_get_attempt": None,
    },
    "url_ttl_seconds": None,
    "http_statuses": {
        "before_approval_download": None,
        "self_approval": None,
        "approved_download": None,
        "other_tenant_download": None,
        "post_revoke_download": None,
        "expired_r2_get": None,
        "old_session_account": None,
        "new_session_revoked_download": None,
    },
    "audit_counts": {
        "download_issued_before_revoke": None,
        "download_issued_after_revoke": None,
        "grant_revoke_events": None,
    },
    "checks": {key: None for key in CHECKS},
}

BANNED_KEYS = re.compile(
    r"(?:^|_)(?:secret|token|password|cookie|authorization|auth_code|"
    r"otp|signed_url|signature|x_amz|patient|email|subject|"
    r"private_key|access_key|refresh_key)(?:_|$)",
    re.IGNORECASE,
)
BANNED_VALUES = re.compile(
    r"(?:https?://|@|X-Amz-|AKIA[0-9A-Z]{16}|sk_[a-zA-Z0-9]+|"
    r"-----BEGIN |Bearer\s|Cookie:)",
    re.IGNORECASE,
)


def _utc_timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ValueError("UTC timestamps must use YYYY-MM-DDTHH:MM:SSZ")
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if parsed.year < 2026:
        raise ValueError("UTC staging timestamp predates the project")
    return parsed


def evaluate(report):
    """Return (passed, failures), never claim live confirmation without evidence."""
    issues = []
    if not isinstance(report, dict):
        return False, ["Root must be an object"]
    def issue(message):
        issues.append(message)

    # Strict shape avoids accidental inclusion of signed URLs, user identities,
    # or secrets. No arbitrary extra evidence fields are permitted.
    for key, value in TEMPLATE.items():
        if key not in report:
            issue("Missing required field: " + key)
            continue
        if isinstance(value, dict):
            if not isinstance(report[key], dict) or set(report[key]) != set(value):
                issue("Unexpected/missing keys in " + key)
        elif key not in ("git_commit", "test_reference") and report[key] != value:
            issue("Unexpected value for " + key)
    if set(report) != set(TEMPLATE):
        issue("Unexpected root fields; use only the supplied template")

    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if BANNED_KEYS.search(str(key)):
                    issue("Sensitive field names are forbidden")
                inspect(item)
        elif isinstance(value, list):
            issue("Lists are not accepted")
        elif isinstance(value, str) and BANNED_VALUES.search(value):
            issue("Sensitive values and URLs are forbidden")
    inspect(report)
    commit = report.get("git_commit")
    if not isinstance(commit, str) or not re.fullmatch("[a-f0-9]{40}", commit):
        issue("git_commit must be a full 40-character SHA-1")
    reference = report.get("test_reference")
    if not isinstance(reference, str) or not re.fullmatch("[A-Z0-9-]{8,64}", reference):
        issue("test_reference must be a synthetic non-personal label")
    checks = report.get("checks")
    if not isinstance(checks, dict) or any(checks.get(k) is not True for k in CHECKS):
        issue("All explicit operator checks must be true; incomplete is PENDING")
    codes = report.get("http_statuses")
    expected_codes = {
        "before_approval_download": 403,
        "self_approval": 403,
        "approved_download": 200,
        "other_tenant_download": 403,
        "post_revoke_download": 403,
        "expired_r2_get": 403,
        "old_session_account": 401,
        "new_session_revoked_download": 403,
    }
    if not isinstance(codes, dict) or any(type(codes.get(k)) is not int or
                                          codes.get(k) != expected for k,expected in expected_codes.items()):
        issue("HTTP response evidence is incomplete or inconsistent with expected status codes")
    ttl = report.get("url_ttl_seconds")
    if type(ttl) is not int or not 1 <= ttl <= 300:
        issue("URL lifetime must be 1 to 300 seconds")
    counts = report.get("audit_counts")
    if (not isinstance(counts, dict) or any(type(counts.get(k)) is not int
            for k in TEMPLATE["audit_counts"])):
        issue("Audit event counts are missing or not integers")
    else:
        before = counts["download_issued_before_revoke"]
        after = counts["download_issued_after_revoke"]
        revoked = counts["grant_revoke_events"]
        if before < 1 or after != before or revoked < 1:
            issue("Audit evidence must show issuance before but not after revocation")
    dates = {}
    ts = report.get("timestamps_utc")
    if isinstance(ts, dict):
        for name in TEMPLATE["timestamps_utc"]:
            try:
                dates[name] = _utc_timestamp(ts.get(name))
            except (ValueError, TypeError):
                issue("Timestamp missing/invalid: " + name)
    else:
        issue("timestamps_utc missing")
    if len(dates) == 4 and type(ttl) is int and 1 <= ttl <= 300:
        if not dates["url_issued"] < dates["grant_revoked"] <= dates["post_revoke_denial"]:
            issue("Revocation and denial must follow signed URL issuance")
        if dates["expired_r2_get_attempt"] < dates["url_issued"] + timedelta(seconds=ttl+30):
            issue("Expired R2 GET must be checked at least 30 seconds past the URL TTL")
    return not issues, issues


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate redacted TCL staging revocation evidence; no network or DB access")
    arg = parser.add_mutually_exclusive_group(required=True)
    arg.add_argument("--template", type=Path, help="Create a NEW JSON evidence template (will not overwrite)")
    arg.add_argument("--file", type=Path, help="Validate an operator-filled JSON evidence report")
    args = parser.parse_args(argv)
    if args.template is not None:
        try:
            with args.template.open("x", encoding="utf-8") as fp:
                json.dump(TEMPLATE, fp, indent=2)
                fp.write("\n")
        except OSError:
            print("ERROR: Cannot create NEW evidence file (or already exists)")
            return 2
        print("Created blank redacted evidence template. No checks have passed.")
        return 0
    try:
        if args.file.stat().st_size > 24_000:
            raise ValueError("Evidence file too large")
        report = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        print("ERROR: Cannot read valid, small evidence JSON")
        return 2
    passed, issues = evaluate(report)
    if not passed:
        print("PENDING/FAIL: Live staging revocation evidence is incomplete or inconsistent.")
        for reason in issues:
            print("-", reason)
        return 1
    print("PASS: Redacted operator evidence meets staging Gate B acceptance criteria.")
    print("IMPORTANT: This validates the report only, not WorkOS/R2 directly.")
    print("Production remains blocked pending independent review and formal approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
