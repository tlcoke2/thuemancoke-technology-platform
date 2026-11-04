"""Guided, offline completion of an existing staging Gate B evidence template.

Operator must individually affirm only checks directly observed in staging.
No guessed statuses or timestamps. Never overwrite the source/evidence copy.
No network calls, clinical DB access, Railway changes, tokens, or URLs.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

try:
    from .validate_revocation_evidence import TEMPLATE, CHECKS, evaluate, progress, _utc_timestamp
except ImportError:
    from validate_revocation_evidence import TEMPLATE, CHECKS, evaluate, progress, _utc_timestamp


PROMPTS = {
    "customer_denied_before_approval":
        "Customer's download request was denied BEFORE grant approval (HTTP 403)",
    "self_approval_denied":
        "The proposing admin was denied approval of their own request (HTTP 403)",
    "separate_mfa_approver":
        "A DIFFERENT appointed administrator approved using fresh MFA",
    "customer_approved":
        "Only independently approved synthetic customer access became active",
    "cross_tenant_customer_denied":
        "A different signed-in tenant/customer was denied the tested grant (HTTP 403)",
    "cross_tenant_membership_hidden":
        "Other-tenant entitlement was absent from that customer's dashboard",
    "grant_revoked":
        "The SYNTHETIC test entitlement was revoked and audited",
    "post_revoke_new_url_denied":
        "A new post-revocation download request returned 403, with NO new URL/audit",
    "old_r2_get_expired":
        "Previously signed R2 GET failed after its ACTUAL TTL plus clock-skew margin",
    "old_gateway_session_denied":
        "Expired/revoked old local gateway session required sign-in (HTTP 401)",
    "new_session_revoked_access_denied":
        "Fresh login still could not download with revoked grant (HTTP 403)",
    "staging_flags_restored":
        "Both staging release flags were restored to their PRE-TEST values",
    "download_did_not_create_license":
        "Confirmed downloading did NOT create or activate any software licence",
    "release_master_untouched":
        "Confirmed signed TEC EPR 1.0.0 master release was unchanged",
    "clinical_databases_untouched":
        "Confirmed no production clinical database was accessed or changed",
}


def _normalise_recorded(report):
    """Convert representations only; do not create new observed facts."""
    for group in ("http_statuses", "audit_counts"):
        values = report.get(group)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            if isinstance(value, str) and re.fullmatch(r"[0-9]{1,5}", value.strip()):
                values[key] = int(value.strip())
    ttl = report.get("url_ttl_seconds")
    if isinstance(ttl, str) and re.fullmatch(r"[0-9]{1,3}", ttl.strip()):
        report["url_ttl_seconds"] = int(ttl.strip())
    timestamps = report.get("timestamps_utc")
    if not isinstance(timestamps, dict):
        return
    for key, value in timestamps.items():
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            # Only convert existing timezone-aware timestamps. No implicit Jamaica/UTC assumption.
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is not None and parsed.utcoffset() is not None:
                timestamps[key] = parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError):
            continue


def _confirm(prompt, ask):
    response = ask(prompt + " [y=observed PASS / n=observed FAIL / Enter=unverified]: ")
    if response.strip().lower() in ("y", "yes"):
        return True
    if response.strip().lower() in ("n", "no"):
        return False
    return None


def complete(report, ask=input, say=print):
    """Make only operator-authorised additions in memory."""
    if not isinstance(report, dict) or not isinstance(report.get("checks"), dict):
        raise ValueError("Expected existing structured Gate B evidence JSON")
    _normalise_recorded(report)
    say("This is an OPERATOR ATTESTATION, not an independent live system audit.")
    say("Never choose PASS for checks not actually witnessed and recorded.")
    for name in CHECKS:
        prior = report["checks"].get(name)
        if prior is True or prior is False:
            continue
        assertion = _confirm(PROMPTS[name], ask)
        if assertion is not None:
            report["checks"][name] = assertion

    dates = report.get("timestamps_utc")
    if isinstance(dates, dict):
        for name in TEMPLATE["timestamps_utc"]:
            try:
                _utc_timestamp(dates.get(name))
            except (ValueError, TypeError):
                say("MISSING/INVALID UTC timestamp: " + name)
                value = ask("Enter ACTUAL recorded UTC YYYY-MM-DDTHH:MM:SSZ, or Enter to leave pending: ").strip()
                if not value:
                    continue
                try:
                    _utc_timestamp(value)
                except ValueError:
                    say("INVALID date: not saved; no time will be guessed.")
                else:
                    dates[name] = value

    # Never select a source commit from the local working-tree head: that might
    # be newer than the code deployed to the staging Railway service.
    if not isinstance(report.get("git_commit"), str) or not re.fullmatch(
        r"[a-f0-9]{40}", report["git_commit"]
    ):
        say("MISSING: full 40-character GIT COMMIT DEPLOYED during the UAT.")
        sha = ask("Paste the deployed Railway SOURCE commit SHA (or Enter to leave pending): ").strip()
        if re.fullmatch(r"[a-f0-9]{40}", sha):
            report["git_commit"] = sha
        elif sha:
            say("INVALID commit SHA: not saved; check Railway Deployments -> Source.")

    ttl = report.get("url_ttl_seconds")
    if type(ttl) is not int or not 1 <= ttl <= 300:
        say("MISSING/INVALID: observed signed R2 URL TTL must be an integer 1–300 seconds.")
        value = ask("Enter ACTUAL observed URL TTL seconds, or Enter to leave pending: ").strip()
        if re.fullmatch(r"[0-9]{1,3}", value) and 1 <= int(value) <= 300:
            report["url_ttl_seconds"] = int(value)
        elif value:
            say("INVALID TTL: no value was guessed.")

    # For any unknown or discrepant status, preserve the actual recorded value;
    # never overwrite a real HTTP 401/403/200 to satisfy a test.
    for name, required in (
        ("before_approval_download",403),("self_approval",403),
        ("approved_download",200),("other_tenant_download",403),
        ("post_revoke_download",403),("expired_r2_get",403),
        ("old_session_account",401),("new_session_revoked_download",403),
    ):
        code = report.get("http_statuses", {}).get(name)
        if type(code) is not int or code != required:
            say("CHECK RECORDED HTTP STATUS: " + name +
                " (acceptance expects integer HTTP " + str(required) + "; unchanged)")
    return report


def main(argv=None, ask=input, say=print):
    parser = argparse.ArgumentParser(description="Review existing staging UAT report with individual operator attestations.")
    parser.add_argument("--input", required=True, type=Path, help="Existing evidence JSON")
    parser.add_argument("--output", required=True, type=Path, help="New reviewed evidence JSON (never overwritten)")
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output must be different")
        if not 0 < args.input.stat().st_size <= 24_000:
            raise ValueError("Input JSON size must be 1–24000 bytes")
        report = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(report, dict) or set(report) != set(TEMPLATE):
            raise ValueError("Unexpected evidence layout; original preserved")
        for group in ("timestamps_utc","http_statuses","audit_counts","checks"):
            if not isinstance(report.get(group), dict) or set(report[group]) != set(TEMPLATE[group]):
                raise ValueError("Unexpected evidence group layout; original preserved")
        complete(report, ask=ask, say=say)
        if args.output.exists():
            raise FileExistsError("Output already exists; choose a new name")
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(report, out, indent=2)
            out.write("\n")
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        # All errors fixed strings / exception type, no raw file content.
        say("ERROR: Cannot process input or create NEW output. Original evidence unchanged.")
        say("Check file existence, JSON validity and that output name has not been used.")
        return 2
    ok, issues = evaluate(report)
    say("Saved a NEW reviewed copy; original evidence was not altered.")
    for line in progress(report):
        say(line)
    if not ok:
        say("PENDING: Do not replace missing observations with assumed PASS values.")
        return 1
    say("PASS: Operator-completed report is consistent; independent live verification and production approval remain separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
