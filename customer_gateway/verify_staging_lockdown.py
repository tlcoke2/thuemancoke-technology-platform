"""Read-only local Railway CLI check of post-UAT staging download switches.

The public /health endpoint only exposes an effective downloadsEnabled bool,
which does not independently prove BOTH switches are false. This tool queries
only the exact isolated staging service and prints only the two boolean
verdicts. Other Railway variables (including secrets) never reach stdout,
logs or files. No Railway changes, no provider auth and no customer requests.
"""
import argparse
import json
import subprocess
import sys


CLI = ("railway", "variable", "list", "--service", "tcl-customer-gateway-staging",
       "--environment", "staging", "--json")
FLAGS = ("GATEWAY_DOWNLOADS_ENABLED", "GATEWAY_RELEASE_APPROVED")


def read_variables(runner=subprocess.run):
    response = runner(CLI, capture_output=True, text=True, timeout=20, check=False)
    if response.returncode != 0 or not 0 < len(response.stdout) < 250_000:
        raise ValueError("Cannot obtain readable staging variables")
    values = json.loads(response.stdout)
    if not isinstance(values, dict):
        raise ValueError("Expected a JSON variable dictionary from Railway")
    return values


def check(values):
    """Only exact off-values count; absence/empty values fail closed."""
    if not isinstance(values, dict):
        raise ValueError("Expected object from Railway CLI")
    checks = {}
    for flag in FLAGS:
        raw = values.get(flag)
        checks[flag] = raw is False or (
            isinstance(raw, str) and raw.strip().lower() == "false"
        )
    return checks


def _decode_stdin(stream):
    # Prevent unlimited allocation and never print raw data: Railway variable
    # lists can contain WorkOS keys, database passwords and R2 credentials.
    raw = stream.read(250_001)
    if not raw or len(raw) > 250_000:
        raise ValueError("Empty or oversized JSON input")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    parsed = json.loads(raw.lstrip("\ufeff"))
    if not isinstance(parsed, dict):
        raise ValueError("Expected Railway variable JSON object")
    return parsed


def main(argv=None, reader=read_variables, say=print, stdin=None):
    cli = argparse.ArgumentParser(description="Verify BOTH Railway staging download flags are false; no secrets printed")
    cli.add_argument("--stdin", action="store_true",
                     help="Read Railway staging variable JSON from stdin instead of launching the Railway CLI")
    args = cli.parse_args(argv)
    try:
        values = _decode_stdin(stdin if stdin is not None else sys.stdin) if args.stdin else reader()
        checks = check(values)
    except (ValueError, TypeError, OSError, TimeoutError, subprocess.SubprocessError,
            json.JSONDecodeError, UnicodeError):
        say("PENDING/FAIL: Unable to verify both staging flags from Railway JSON.")
        say("No variable contents were displayed. For Windows CLI launch issues, use --stdin.")
        return 2
    for flag in FLAGS:
        say(flag + ": " + ("DISABLED" if checks[flag] else "NOT VERIFIED DISABLED"))
    if not all(checks.values()):
        say("PENDING/FAIL: Both staging download switches must be explicitly false.")
        say("No Railway settings were changed by this check.")
        return 1
    say("PASS: Both Railway staging customer gateway download switches are explicitly disabled.")
    say("LIMITATION: Railway config state and public runtime readiness are separate checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
