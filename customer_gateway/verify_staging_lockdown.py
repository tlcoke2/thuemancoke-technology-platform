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


def main(argv=None, reader=read_variables, say=print):
    cli = argparse.ArgumentParser(description="Verify BOTH Railway staging download flags are false; no secrets printed")
    cli.parse_args(argv)
    try:
        checks = check(reader())
    except (ValueError, TypeError, OSError, TimeoutError, subprocess.SubprocessError,
            json.JSONDecodeError):
        say("PENDING/FAIL: Cannot confirm Railway staging flags using read-only CLI.")
        say("No variables or credentials displayed. Check linked project and Railway CLI access.")
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
