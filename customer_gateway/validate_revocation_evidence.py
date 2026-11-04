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
        elif key not in ("git_commit", "test_reference", "url_ttl_seconds") and report[key] != value:
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



def progress(report):
    """Return a redacted completion summary, never display evidence values."""
    if not isinstance(report, dict):
        return ["Invalid report structure; start from --template"]
    lines = []
    for group in ("timestamps_utc", "http_statuses", "audit_counts", "checks"):
        expected = TEMPLATE[group]
        submitted = report.get(group)
        if not isinstance(submitted, dict):
            lines.append(group + ": missing section")
            continue
        missing = [key for key in expected if submitted.get(key) is None]
        incomplete = [key for key in expected if key not in missing
                      and group == "checks" and submitted.get(key) is not True]
        total = len(expected)
        completed = total - len(missing) - len(incomplete)
        lines.append(group + ": " + str(completed) + "/" + str(total) + " recorded")
        for name in missing + incomplete:
            lines.append("  - PENDING: " + group + "." + name)
        if set(submitted) != set(expected):
            lines.append("  - WARNING: unexpected/missing field names")
    # "Recorded" means present, not valid. Surface field-specific failures
    # without ever echoing confidential values supplied by the operator.
    timestamps = report.get("timestamps_utc")
    if isinstance(timestamps, dict):
        for name in TEMPLATE["timestamps_utc"]:
            if timestamps.get(name) is not None:
                try:
                    _utc_timestamp(timestamps[name])
                except (ValueError, TypeError):
                    lines.append("  - INVALID: timestamps_utc." + name +
                                 " (required: actual UTC YYYY-MM-DDTHH:MM:SSZ)")
    statuses = report.get("http_statuses")
    expected_statuses = {
        "before_approval_download": 403,
        "self_approval": 403,
        "approved_download": 200,
        "other_tenant_download": 403,
        "post_revoke_download": 403,
        "expired_r2_get": 403,
        "old_session_account": 401,
        "new_session_revoked_download": 403,
    }
    if isinstance(statuses, dict):
        for name, expected in expected_statuses.items():
            actual = statuses.get(name)
            if actual is not None and (type(actual) is not int or actual != expected):
                lines.append("  - INVALID: http_statuses." + name +
                             " (expected observed numeric HTTP " + str(expected) + ")")
    for name in ("git_commit", "url_ttl_seconds"):
        if report.get(name) in (None, ""):
            lines.append("PENDING: " + name)
    # The deployed commit is not necessarily the current checkout head.
    commit = report.get("git_commit")
    if commit not in (None, "") and (
            not isinstance(commit, str) or not re.fullmatch("[a-f0-9]{40}", commit)):
        lines.append("INVALID: git_commit (must be actual deployed 40-character SHA)")
    ttl = report.get("url_ttl_seconds")
    if ttl is not None and (type(ttl) is not int or not 1 <= ttl <= 300):
        lines.append("INVALID: url_ttl_seconds (must be observed integer from 1 to 300)")
    success, reasons = evaluate(report)
    lines.append("Final validator: " + ("PASS (report consistency only)" if success
                  else "PENDING/FAIL (" + str(len(reasons)) + " issues)"))
    lines.append("This offline checker cannot attest live WorkOS/R2 outcomes.")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate redacted TCL staging revocation evidence; no network or DB access")
    arg = parser.add_mutually_exclusive_group(required=True)
    arg.add_argument("--template", type=Path, help="Create a NEW JSON evidence template (will not overwrite)")
    arg.add_argument("--file", type=Path, help="Validate an operator-filled JSON evidence report")
    arg.add_argument("--progress", type=Path,
                     help="Show missing sections of a redacted report, without exposing values")
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
    report_path = args.file if args.file is not None else args.progress
    try:
        size = report_path.stat().st_size
        if size == 0:
            print("ERROR: Evidence file is empty. Preserve the original and inspect it in Notepad.")
            return 2
        if size > 24_000:
            print("ERROR: Evidence JSON exceeds the 24,000-byte safety limit.")
            return 2
        # Windows Notepad can write UTF-8 with a BOM; utf-8-sig handles
        # both forms without changing the user's evidence file.
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print("ERROR: Evidence file not found at the supplied path.")
        return 2
    except PermissionError:
        print("ERROR: Evidence file cannot be read (access denied).")
        return 2
    except IsADirectoryError:
        print("ERROR: Expected an evidence JSON file, not a directory.")
        return 2
    except UnicodeError:
        print("ERROR: Evidence file is not valid UTF-8 JSON. Save a separate UTF-8 copy, preserving the original.")
        return 2
    except json.JSONDecodeError as error:
        # Print only location, never JSON fragments that could contain secrets.
        print("ERROR: Invalid JSON syntax at line " + str(error.lineno)
              + ", column " + str(error.colno)
              + ". Check commas, quotes and brackets; do not paste confidential content.")
        return 2
    except OSError:
        print("ERROR: Evidence file is inaccessible or unreadable.")
        return 2
    if args.progress is not None:
        for line in progress(report):
            print(line)
        # The progress command reports incomplete evidence as PENDING
        # without asking the operator to fabricate any success flags.
        return 0 if evaluate(report)[0] else 1
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
