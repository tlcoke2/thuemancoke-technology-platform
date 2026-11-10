"""Repair formatting in a local staging UAT evidence *copy* through operator input.

No inferred successes, no database/network operations, and no modification of
the source JSON. Only the operator's *actual observed* HTTP statuses and
timestamps are accepted. A consistent report is not independent live attestation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

try:
    from .validate_revocation_evidence import TEMPLATE, evaluate, progress, _utc_timestamp
except ImportError:
    from validate_revocation_evidence import TEMPLATE, evaluate, progress, _utc_timestamp

HTTP_EXPECTED = {
    "before_approval_download": 403,
    "self_approval": 403,
    "approved_download": 200,
    "other_tenant_download": 403,
    "post_revoke_download": 403,
    "expired_r2_get": 403,
    "old_session_account": 401,
    "new_session_revoked_download": 403,
}
OFFSET_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})"
)


def explicit_utc(value):
    """Convert an explicit offset-aware, second-precision time to canonical UTC."""
    if not OFFSET_TIMESTAMP.fullmatch(value):
        raise ValueError("Must include seconds and a timezone offset or Z")
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("Timezone is required")
    utc = moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _utc_timestamp(utc)
    return utc


def repair(report, ask=input, say=print):
    """Modify a copy in memory, retaining previous check attestations."""
    say("Editing recorded evidence representation; no test outcomes are assumed.")
    say("Use only REAL observed status codes, timestamps and Railway deployment SHA.")
    dates = report["timestamps_utc"]
    for name in TEMPLATE["timestamps_utc"]:
        original = dates.get(name)
        try:
            _utc_timestamp(original)
            continue
        except (ValueError, TypeError):
            pass
        say("INVALID/UNKNOWN UTC timestamp: " + name)
        say("Enter actual YYYY-MM-DDTHH:MM:SSZ (UTC) OR actual offset timestamp such as 2026-11-04T11:24:36-05:00 (Jamaica local).")
        entered = ask("Actual recorded timestamp (Enter=keep pending): ").strip()
        if not entered:
            continue
        try:
            dates[name] = explicit_utc(entered)
        except (ValueError, OverflowError):
            say("Not saved: invalid or ambiguous timestamp. Never infer the missing time.")

    codes = report["http_statuses"]
    for name, expected in HTTP_EXPECTED.items():
        recorded = codes.get(name)
        if type(recorded) is int and recorded == expected:
            continue
        # Only string-to-number conversion preserves the literal recorded
        # observation; it must still be the acceptance-expected value.
        if isinstance(recorded, str) and re.fullmatch(r"[0-9]{3}", recorded.strip()):
            codes[name] = int(recorded.strip())
            if codes[name] == expected:
                continue
        say("MISSING/INVALID actual HTTP status for: " + name)
        say("Acceptance expects " + str(expected) + "; enter the ACTUAL observed response, not a guessed expected code.")
        entered = ask("Actual observed numeric HTTP status (Enter=keep pending): ").strip()
        if not entered:
            continue
        if re.fullmatch(r"[1-5][0-9]{2}", entered):
            codes[name] = int(entered)
        else:
            say("Not saved: provide a valid 3-digit HTTP response you actually observed.")

    commit = report.get("git_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        say("Missing Git deployment source commit. A 64-character file SHA-256 is NOT a Git commit.")
        say("Open Railway -> staging gateway service -> Deployments -> deployment used for UAT -> Source.")
        entry = ask("Actual 40-character deployed SOURCE Git SHA (no quotes; Enter=pending): ").strip().lower()
        if re.fullmatch(r"[0-9a-f]{40}", entry):
            report["git_commit"] = entry
        elif entry:
            say("Not saved: a Git SHA-1 commit must be exactly 40 hex characters.")

    # Never alter check flags or audit counts. The operator previously
    # attested all 15 flags; this script is for format correction only.
    return report


def main(argv=None, ask=input, say=print):
    cli = argparse.ArgumentParser(
        description="Guided correction of an existing UAT evidence report; writes only a NEW file."
    )
    cli.add_argument("--input", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve() or args.output.exists():
            say("ERROR: Output must be a different, unused file. No changes made.")
            return 2
        if not 0 < args.input.stat().st_size <= 24_000:
            say("ERROR: Input missing/empty/oversized. Original unchanged.")
            return 2
        report = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(report, dict) or set(report) != set(TEMPLATE):
            say("ERROR: Invalid evidence document layout; original unchanged.")
            return 2
        for group in ("checks", "http_statuses", "timestamps_utc", "audit_counts"):
            if not isinstance(report.get(group), dict) or set(report[group]) != set(TEMPLATE[group]):
                say("ERROR: Invalid evidence group structure. Original unchanged.")
                return 2
        repair(report, ask=ask, say=say)
        # x mode protects prior evidence even if another process creates the path.
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    except (OSError, UnicodeError, ValueError, TypeError):
        say("ERROR: Unable to read or write evidence. Source left unchanged.")
        return 2
    say("Saved a NEW corrected evidence report; originals were not overwritten.")
    for line in progress(report):
        say(line)
    passed, _ = evaluate(report)
    if not passed:
        say("PENDING: Only actual observed evidence may be recorded. No results were fabricated.")
        return 1
    say("PASS: Local report is internally consistent; independent live security review remains mandatory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
