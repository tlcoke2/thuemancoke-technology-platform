# Gate B — Live staging customer entitlement revocation and isolation

**Environment:** TCL customer gateway staging ONLY. **Status:** Owner-reported staging UAT; complete HTTP/audit evidence not yet attested.

This test does not authorise production downloads. It must use dedicated staging customer records, never real patients, CRM records or clinical databases. Do not touch the signed TEC EPR Clinic Edition 1.0.0 master archive, publisher private key or R2 object. The SHA-256/signature/full-archive binding acceptance (Gate A3) has already passed, separately.

## Preconditions and safeguards

- Confirm Railway is linked to project `bountiful-curiosity`, environment `staging`, and service `tcl-customer-gateway-staging`. Check the public `/health` and `/ready` endpoints. `APP_ENV=staging` remains mandatory; `from_environment()` intentionally rejects other environments.
- Record the latest deployed staging commit, distinct active WorkOS test identities (administrator A, administrator B and synthetic customer C), and a different synthetic customer D for isolation. Appointed administrators must have *current* authenticator verification. Customer C must NOT be an administrator or member of D's tenant.
- The two download switches `GATEWAY_DOWNLOADS_ENABLED` and `GATEWAY_RELEASE_APPROVED` must only be enabled within an approved, time-bounded staging acceptance window. Capture their prior values (not secrets) before touching Railway configuration. Restore those exact values after testing. Do not enable production controls simply to test a UI.
- Use only a synthetic/explicitly approved grant with a short access interval and valid test-contract and review-reference text. Do NOT revoke an existing genuine customer grant.
- Record **UTC timestamps and outcomes**, but NEVER record signed URL query strings, WorkOS codes/cookies, R2 credentials, authentication codes, or personal/patient information.

## Execution and acceptance criteria

| # | Operator action | Expected security result | Evidence to retain |
|---|---|---|---|
| 1 | Customer C signs in **before** any approval. | No approved download button; issuance denied and no URL issued. | UTC time, HTTP status / UI state, synthetic test label. |
| 2 | Administrator A (fresh MFA) proposes a synthetic customer; administrator A attempts self-approval. | Proposal is pending/inactive; self-approval denied. | Synthetic grant reference and redacted `customer_proposed` audit. |
| 3 | Different appointed administrator B (fresh MFA) approves. | Only the correctly matched customer membership and grant become active. | Redacted `customer_approved` audit event; proposer ≠ approver. |
| 4 | Confirm that both staging release flags are explicitly enabled for this narrow test. Customer C signs in and requests ONE private URL. | HTTP 200 with a signed URL limited by policy to at most **300 seconds**; `download_link_issued` audit records only the event, actor/grant reference and time, **not the URL**. | UTC issuance time, expiry in seconds and redacted audit event. |
| 5 | Customer D signs in as an unauthorised other-tenant identity. | Customer D cannot view C's customer membership or issue a URL for C's grant; denied HTTP 403. | UI screenshot with no secrets and status. |
| 6 | Administrator B, with fresh MFA, revokes **only the synthetic test grant**. | The grant changes to `revoked`, and `grant_revoked` audit event is present. | UTC revocation time and audit status. |
| 7 | Customer C refreshes `/customer`. Also submit a **previously open** (stale) download form once, if retained in a separate customer tab. | No active download button; prior stale POST is HTTP **403**; no *new* R2 URL is returned or newly audited after revoke. | Redacted status and before/after issuance event count. |
| 8 | After the **original** signed GET URL's own expiry (plus sensible clock-skew margin), attempt the expired link in the test browser, without sharing/copying the URL. | Expired presigned R2 GET must fail. **Do not use HEAD as evidence** for a GET-signed URL. | Expiry time and non-sensitive HTTP result; never expose URL. |
| 9 | Expire/revoke customer's local gateway session; test re-access. | `/account` requires sign-in; revoked grant remains unavailable after new login. | UI status and UTC time. |
| 10 | Restore **prior staging flag values**, inspect the synthetic grant and saved redacted evidence. | No ongoing test exposure; no licence issued, no master, R2 object or clinical DB changes. | Flag state, audit review and sign-off names. |

## Critical limitation: existing signed R2 URLs

Database grant revocation prevents **new URL issuance only**. It **does not instantly revoke an already-issued** Cloudflare R2 presigned GET bearer URL. Previously issued URLs remain usable until their expiry (up to 300 seconds, potentially subject to clock skew). This distinction is an explicit production-acceptance decision. If immediate cessation of active downloads is required, do not approve direct R2 presigned GET distribution; redesign with a reauthorising delivery proxy or another active revocation mechanism and retest.

## Read-only evidence and conclusion

Record the test date, Git commit, staging service/environment, synthetic grant reference, operator roles A/B/C/D (no private tokens), the key UTC timestamps, expected vs. observed HTTP statuses, audit event counts and resulting staging flag state. Save evidence to an appropriately restricted organisational location, not a public pull-request comment. The successful Gate A3 verification produced 442 manifest-file matches and 3 signing metadata matches, but that is not evidence that Gate B passed.

**Pass criteria:** Every negative authorization check returns denied; only independently approved access issues a link; revocation stops new issuance; tenant isolation holds; existing link stops functioning after its own expiry; flags are restored. Any ambiguous result = **FAIL/PENDING**, not pass. PR #38 remains draft, commercial production approval remains separate.

## Read-only evidence completion (new)

The owner has shown a synthetic grant in `revoked` state and another in
`approved` state, after reporting a successful staging test. This is useful
but is not sufficient by itself to prove that a revoked grant can no longer
issue new links or that a different customer was denied. Do **not** repeat
writes merely to satisfy documentation; if a required earlier HTTP result
was not recorded, label it `PENDING` and use a **fresh isolated synthetic
grant** for a controlled retest.

A **local, fail-closed report validator** is provided:
`validate_revocation_evidence.py`. It makes **no network requests or DB
changes**; it only checks the coherence of an operator's **redacted,
manually recorded** results. It deliberately refuses unknown fields,
URLs, email addresses and credential-looking keys. It is not an independent
WorkOS, Railway or Cloudflare attestation and cannot turn a report into
cryptographic proof.

Create a **new private template** on the trusted workstation:

```powershell
cd C:\My_Applications\TCL-gateway-verification
git pull --ff-only origin feature/gateway-entitlement-approvals
python .\customer_gateway\validate_revocation_evidence.py --template "$env:USERPROFILE\Downloads\TCL-stage-B-evidence.json"
```

The operator has already created a blank `TCL-stage-B-evidence.json`
template. **Do not run `--template` again against that filename**: the tool
correctly refuses to overwrite it. Review or edit the existing local file
with `notepad "$env:USERPROFILE\\Downloads\\TCL-stage-B-evidence.json"`
(or a trusted code editor). The `--progress` command lists only outstanding
field names and never prints confidential evidence values:

```powershell
python .\\customer_gateway\\validate_revocation_evidence.py --progress "$env:USERPROFILE\\Downloads\\TCL-stage-B-evidence.json"
```

Then record the **actually observed** staging-only values; do not include
grant IDs, subject IDs, email addresses, token strings, cookies, R2 signed
URLs, secrets or patient data. Use UTC `YYYY-MM-DDTHH:MM:SSZ` timestamps.
An unknown observation remains `null`; **never enter `true`, `200` or
`403` just to make the validator pass**. The supplied `git_commit` must
be the **deployed staging service's** commit at the time of the UAT, not
the latest local/git branch revision by assumption. Run:

```powershell
python .\customer_gateway\validate_revocation_evidence.py --file "$env:USERPROFILE\Downloads\TCL-stage-B-evidence.json"
```

A `PASS` only confirms that a **completed operator report** is internally
consistent with the Gate B acceptance checklist. Retain a protected copy and
perform independent security review before sign-off. A `PENDING/FAIL` does
not undo the already verified release integrity or revoke customer access.

**End-of-test hygiene:** The older synthetic `approved` entitlement shown
in the review UI is not automatically cleaned up by this offline validator.
An appointed administrator should deliberately revoke it after all approved
staging tests, using the authenticated CSRF-protected gateway controls.
Never manipulate the staging database or synthetic grants using a production
clinical/CRM connection.
