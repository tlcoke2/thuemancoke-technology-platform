# Staging Gate B — Railway CLI deployment provenance

The TCL owner ran the offline staging acceptance checks and confirmed all 15
operator observations; the local JSON report now has valid UTC timestamps,
expected HTTP statuses and unchanged audit counts. Its only outstanding field
is `git_commit`: Railway CLI reported deployment UUIDs and UTC creation times,
but **no `meta.commitHash`**. A Railway deployment ID is not a Git SHA.

**Do not paste a Railway UUID into the 40-character Git commit field.**
Do not invent a Git commit, substitute the SHA-256 of an application file,
or use the latest GitHub checkout as evidence of an earlier staging upload.

The validator now accepts **either** a real 40-character source Git commit,
**or** the following two exact alternative metadata fields when Git SHA is
absent from the actual Railway deployment record:

- `railway_deployment_id`: actual 36-character deployment UUID from Railway.
- `railway_deployment_created_at`: actual `createdAt` in UTC, including optional
  fractional seconds; e.g. `2026-11-04T15:57:02.500Z`.

This is **backwards-compatible**: existing reports require no schema update
unless using Railway alternative provenance. The validator checks the UUID,
time syntax, creation time <= signed URL issuance, expiry and acceptance
timestamps, and the other Gate B controls. It **cannot independently prove**
which code bytes were deployed by a CLI upload, nor verify WorkOS and R2 live.

## Safe operator workflow (Windows PowerShell)

The owner is already linked to TCL staging service
`tcl-customer-gateway-staging` in Railway project `bountiful-curiosity`.
First verify that the linked service/environment is still the expected one.

```powershell
cd C:\My_Applications\TCL-gateway-verification
git pull --ff-only origin feature/gateway-entitlement-approvals
railway status

$final = Join-Path $env:USERPROFILE 'Downloads\TCL-stage-B-evidence-final.json'
$railwayList = Join-Path $env:USERPROFILE 'Downloads\TCL-staging-deployments.json'
$withProvenance = Join-Path $env:USERPROFILE 'Downloads\TCL-stage-B-evidence-with-provenance.json'

railway deployment list --service tcl-customer-gateway-staging --environment staging --limit 30 --json |
    Set-Content -LiteralPath $railwayList -Encoding utf8

python .\customer_gateway\record_railway_provenance.py --input "$final" --railway-list "$railwayList" --output "$withProvenance"

python .\customer_gateway\validate_revocation_evidence.py --file "$withProvenance"
```

Both `$final` and `$railwayList` are **read only inputs** to the Python
program. The final evidence is written **exclusively to a new pathname**;
existing reports are never overwritten. Do not add signed URLs, R2 keys,
WorkOS cookies, MFA codes, patient records or personal identifiers.

The program chooses the latest CLI-listed deployment **created before** the
report's recorded signed URL issuance, rejects a redeployment in the core
issuance-to-revocation-denial window, and uses the actual `createdAt` of
the selected deployment. If Railway ever includes a proper 40-character
`meta.commitHash`, it uses that instead. It cannot retrospectively guarantee
that a deployment record has a complete history: the operator must ensure
the CLI list covers the original UAT window and same service/environment.

**Operator-supplied deployment examples:** `0fb03434-435e-4317-a55b-fb1ed49f9440`
was created `2026-11-04T12:27:09.187Z` and later removed;
`b56fd4e9-4299-4bb8-857d-185099bf8141` was created
`2026-11-04T15:57:02.500Z` and is now online. These records refer to
*different deployments*. Do not assume either is the tested deployment:
the report's **actual** `url_issued` timestamp must determine the correct
one. In particular, an earlier removed deployment must not be used to
identify a test that occurred after a newer deployment was created.

A local report PASS is **operator-recorded staging evidence consistency only**.
Independent review of the source deployment, provider logs and R2 expiration
test remains a production acceptance gate. PR #38 stays draft, downloads
and the public site are not activated as a consequence of this workflow.
