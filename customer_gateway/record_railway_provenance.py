"""Attach Railway deployment metadata to a COPY of redacted staging UAT evidence.

The Railway CLI's deployment list has no Git commit for CLI uploads. Select
the latest deployment created before the URL issuance, reject an intervening
deployment before post-revocation denial, and never claim to attest source
bytes. No Railway network requests; only local CLI JSON + local evidence.
"""
import argparse
from datetime import timezone
import json
from pathlib import Path
import re

try:
    from .validate_revocation_evidence import (
        TEMPLATE, RAILWAY_PROVENANCE_FIELDS, railway_created_at, _utc_timestamp,
        evaluate, progress,
    )
except ImportError:
    from validate_revocation_evidence import (
        TEMPLATE, RAILWAY_PROVENANCE_FIELDS, railway_created_at, _utc_timestamp,
        evaluate, progress,
    )

ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def select_deployment(report, entries):
    """Return the CLI-listed deployment active throughout the core UAT window.

    The list must include every deployment during that window. If it is
    truncated or the chosen deployment has an unknown status, do not proceed.
    """
    if not isinstance(entries, list) or not entries:
        raise ValueError("Railway list must contain deployment records")
    started = _utc_timestamp(report["timestamps_utc"]["url_issued"])
    denied = _utc_timestamp(report["timestamps_utc"]["post_revoke_denial"])
    if denied < started:
        raise ValueError("Revocation denial cannot precede issuance")
    candidates=[]
    seen=set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Unexpected Railway deployment record")
        ident=entry.get("id")
        when=entry.get("createdAt")
        status=entry.get("status")
        if not isinstance(ident,str) or not ID.fullmatch(ident):
            raise ValueError("Missing/invalid Railway deployment UUID")
        if ident in seen:
            raise ValueError("Duplicate Railway deployment UUID")
        seen.add(ident)
        created=railway_created_at(when)
        if status not in ("SUCCESS","REMOVED","FAILED","CRASHED","BUILDING",
                          "DEPLOYING","INITIALIZING","WAITING","QUEUED","SLEEPING"):
            raise ValueError("Unknown Railway deployment status")
        # A new release created in the core test window makes single-version
        # attribution ambiguous and requires explicit operator reconciliation.
        if started < created <= denied:
            raise ValueError("Gateway was redeployed during issuance/revocation test interval")
        if created <= started:
            candidates.append((created,entry))
    if not candidates:
        raise ValueError("No Railway deployment predates recorded UAT issuance")
    candidates.sort(key=lambda pair:pair[0])
    chosen=candidates[-1][1]
    if chosen["status"] not in ("SUCCESS","REMOVED"):
        raise ValueError("Selected deployment was not recorded as successful/removed")
    return chosen


def attach(report, deployments):
    if not isinstance(report,dict) or set(report)!=set(TEMPLATE):
        raise ValueError("Expected the existing unmodified legacy evidence layout")
    if report.get("git_commit") not in ("",None):
        raise ValueError("Existing Git commit recorded; do not attach a second provenance method")
    for name in ("timestamps_utc","http_statuses","audit_counts","checks"):
        if not isinstance(report.get(name),dict) or set(report[name])!=set(TEMPLATE[name]):
            raise ValueError("Incomplete or inconsistent evidence schema")
    selected=select_deployment(report,deployments)
    metadata=selected.get("meta") or {}
    if not isinstance(metadata,dict):
        raise ValueError("Malformed Railway metadata")
    sha=metadata.get("commitHash")
    if isinstance(sha,str) and re.fullmatch(r"[a-f0-9]{40}",sha):
        report["git_commit"]=sha
        return "Git commit associated with the deployment"
    # No Git commit in Railway's deployment JSON: do not insert a file digest.
    report["railway_deployment_id"]=selected["id"]
    report["railway_deployment_created_at"]=selected["createdAt"]
    if RAILWAY_PROVENANCE_FIELDS-set(report):
        raise ValueError("Missing Railway alternative provenance fields")
    return "Railway deployment UUID + timestamp (no Git SHA supplied by Railway)"


def main(argv=None):
    cli=argparse.ArgumentParser(description="Record CLI-observed Railway deployment metadata in a NEW staging evidence copy")
    cli.add_argument("--input",type=Path,required=True)
    cli.add_argument("--railway-list",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args(argv)
    try:
        if args.output.resolve() in (args.input.resolve(),args.railway_list.resolve()):
            raise ValueError("Output cannot overwrite an input file")
        if args.output.exists():
            raise ValueError("Output already exists; choose a new filename")
        if not (0 < args.input.stat().st_size <= 24_000):
            raise ValueError("Unexpected evidence size")
        if not (0 < args.railway_list.stat().st_size <= 1_000_000):
            raise ValueError("Unexpected Railway metadata size")
        evidence=json.loads(args.input.read_text(encoding="utf-8-sig"))
        raw=json.loads(args.railway_list.read_text(encoding="utf-8-sig"))
        listing=raw.get("deployments") if isinstance(raw,dict) else raw
        mode=attach(evidence,listing)
        with args.output.open("x",encoding="utf-8") as output:
            json.dump(evidence,output,indent=2)
            output.write("\n")
    except (OSError,TypeError,ValueError,KeyError,UnicodeError):
        print("ERROR: Could not match deployment metadata to UAT timestamps, or destination exists.")
        print("No input file changed. Verify gateway service, staging environment and full deployment list.")
        return 2
    print("Recorded provenance method: "+mode)
    print("Recorded the latest Railway deployment preceding UAT issuance with no core-window redeployment.")
    print("This check trusts the local CLI export; it does not independently attest deployed source.")
    for line in progress(evidence):
        print(line)
    ok,_=evaluate(evidence)
    if not ok:
        print("PENDING: Remaining evidence must be resolved before acceptance.")
        return 1
    print("PASS: Redacted UAT report consistency only; independent review remains required.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
