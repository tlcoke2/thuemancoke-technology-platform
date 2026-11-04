# TCL Customer Gateway — independent staging-to-production assurance

**Status:** Owner reports independent WorkOS and Cloudflare R2 tests complete and owner-signed; the underlying evidence is not attached to GitHub. Other commercial and production-specific controls remain PENDING. **Scope:** Staging only; no production cutover.

## Evidence already reported by the operator (4 November 2026)

- Signed TEC EPR Clinic Edition v1.0.0 payload was read back and independently checked locally against the pinned publisher public key, RSA-SHA256 detached manifest signature, pinned archive SHA-256/length, 442 signed manifest members and 3 signing metadata members (**Gate A3, owner-reported integrity PASS**).
- The operator completed an isolated, synthetic **Gate B** entitlement/revocation UAT and individually marked 15/15 items as observed. The saved evidence has 4/4 UTC timestamps, 8/8 policy-expected numerical HTTP statuses and 3/3 event counts.
- The actual Railway staging deployment UUID + UTC creation timestamp from a CLI-exported deployment list were attached as **alternative deployment provenance**, because Railway did not populate `meta.commitHash` for the test deployment. The offline verifier explicitly checked the UAT timing window.
- The owner ran `validate_revocation_evidence.py --file "$withProvenance"` and reported:
  `PASS: Redacted operator evidence meets staging Gate B acceptance criteria.`

**Interpretation:** Operator-recorded evidence is complete and locally self-consistent. This is **NOT** independent confirmation that WorkOS, Railway, PostgreSQL or Cloudflare R2 actually behaved as asserted. A Railway deployment UUID identifies a deployment record but does **not** cryptographically bind a CLI upload to particular source bytes. Retain the sensitive detailed report locally or in restricted organisational evidence storage. Do not upload it, source IDs, cookies, presigned URLs, user email/subject IDs or health information to GitHub.

## Independent reviewer acceptance checklist

The reviewer must not simply accept an existing check mark or rerun the offline validator. For each item, inspect suitably redacted independent provider records, deployment configuration, focused reproductions in an authorised isolated staging environment or other direct evidence.

| Control | Independent review test / evidence | State |
| --- | --- | --- |
| B1. Deployment provenance | Correlate recorded UAT deployment UUID with Railway history, service/environment, exact creation UTC, deployed image/source build artefacts. Document whether code-to-image integrity can be established or must remain an explicit residual risk. | **PENDING** |
| B2. Two-person customer approval | Distinct appointed admin identities; fresh MFA and CSRF; proposer self-approval fails; legitimate independent approval succeeds. Protect identifiers from public evidence. | **PENDING** |
| B3. Customer/tenant isolation | Distinct synthetic identities/tenants, hidden foreign grants and server-side denial of a different tenant's download request; inspect 403 response and no URL release. | **PENDING** |
| B4. Revocation enforcement | Actual grant revoked in staging; formerly approved customer retries the stale POST; inspect 403 and zero additional `download_link_issued` audit events. | **PENDING** |
| B5. Presigned R2 GET expiry | Original GET-signed bearer URL (not HEAD) fails after its exact TTL plus skew, without pasting URL into logs or issue comments. Confirm TTL <= 300 seconds. | **PENDING** |
| B6. Identity and session termination | Distinguish local session deletion/expiry from WorkOS SSO provider-session revocation; assess account disabling, re-login and fresh-session treatment. | **PENDING** |
| B7. Private R2 access | Verify bucket is private; dedicated minimum read-only Object credentials (ideally one object/prefix); no `PutObject`, `DeleteObject` or public listing. Confirm R2 secret rotation and log redaction. | **PENDING** |
| B8. Authentication hardening | WorkOS redirect allowlist, PKCE/state, session cookie flags, CSRF, MFA fail-closed behaviour, session rotation and spoofed headers/forwarded-origin protection. | **PENDING** |
| B9. Audit and security operations | Check audit event uniqueness, transaction boundary, retention/export, security monitoring, rate limits, suspicious-login review, alerting and least-privileged log access. | **PENDING** |
| B10. Segregation | Verify dedicated gateway Postgres, separate CRM and clinical stores, correct staging-only flag environment, and no patient data copied to evidence. | **PENDING** |
| B11. Deployment and release controls | Verify CI tests, review of remaining High vulnerability, pinned release signer/hash, secrets storage, immutable release artefacts, rollback and disaster recovery. | **PENDING** |
| B12. Commercial licence controls | Confirm download alone creates no licence, user registration/terms/privacy are appropriate and actual subscription, entitlement and activation flows are approved before production distribution. | **PENDING** |

## Residual-risk decisions that must be explicit

1. **Already-minted R2 presigned GET links cannot be revoked immediately.** Database revocation only blocks *new* link issuance. Before production, obtain an explicit, documented business risk acceptance of a maximum 300-second exposure window **or** redesign to a re-authorising delivery proxy and retest.
2. **Local session != WorkOS provider session.** Local logout or 15-minute expiration does not terminate WorkOS SSO automatically. Decide provider-session revocation, account disable response, forced reauthentication, idle/session lifetime and webhook policy.
3. **Railway CLI deployment metadata is not a signed provenance attestation.** Determine whether to introduce a reproducible source commit/build artifact digest, container signing or provenance manifest before accepting commercial deployment.
4. **Previously approved synthetic customer test grants** must be revoked or allowed to expire under staging controls; confirm all staging-only R2 flags restored. Do not revoke genuine customer data.

## Formal gate and sign-off

**Gate B1 — operator-reported staging test and local report consistency:** **PASS (OWNER-REPORTED).**

**Gate B2 — independent security verification:** **PENDING** until evidence above is independently evaluated, material vulnerabilities remediated or risk-accepted with rationale, and an authorised reviewer signs the dated decision.

**Gate C — production readiness:** **PENDING** until Gate B2 is approved, production environment and dedicated database are separately reviewed, a secure custom TCL gateway hostname and exact WorkOS redirects configured, documented licensing/privacy/terms in place, and owner gives an explicit go/no-go.

**Release action:** PR #38 and PR #39 must stay draft; do not merge, deploy customer production, turn on release flags, or enable the TCL website public sign-in CTA based on local evidence alone. When ready, record reviewer identity/role, date, evidence locations (private references only), accepted residual risks and rollback owner in a protected sign-off document, not in a public GitHub issue.

## Read-only public staging preflight — owner-reported PASS after lockdown

A narrow tool is included to check only two public endpoints of the **exact**
Railway staging gateway hostname that the owner previously confirmed. It uses
HTTPS certificate validation, explicitly refuses redirects, sends no cookies
or credentials, limits response size and makes **GET requests only**:

~~~powershell
cd C:\My_Applications\TCL-gateway-verification
git pull --ff-only origin feature/gateway-entitlement-approvals
python .\customer_gateway\public_staging_preflight.py --origin "https://tcl-customer-gateway-staging-staging.up.railway.app"
~~~

The checker requests `/health` and `/ready`, checks HTTPS response security
headers, confirms `environment=staging`, `downloadsEnabled=false`,
`mfaStepUpEnabled=true`, `authenticatorSetupAvailable=false`, and
`ready=true`. A FAIL/PENDING can indicate a genuine readiness gap or
staging configuration drift. Do not turn downloads on to make this test
pass. Closing first-time authenticator enrolment should be verified in
Railway staging configuration by an authorised operator before trusting
the public report.

**Limits:** The public health endpoint's `downloadsEnabled=false` alone
cannot prove both underlying variables are individually false, and a
`ready` response checks the gateway database only at that moment. This
is a public, passive, unauthenticated smoke test; not independent customer
grant testing, R2 credential scope verification, WorkOS session validation,
Railway image-source attestation, or commercial certification.

## New dependency vulnerability gate — source-only CI

`.github/workflows/customer-gateway.yml` includes a blocking `pip-audit`
check of `customer_gateway/requirements.txt` and its resolved dependencies.
A failed advisory audit must be triaged before production readiness approval;
it does not automatically authorise dependency upgrades or runtime changes.
The check runs in GitHub Actions and does not deploy to Railway.


## Staging lockdown recheck — owner report, 4 November 2026

The first public preflight flagged effective downloads as enabled. The operator then independently changed both staging download-control switches to disabled and observed a successful new staging deployment, identified as `6aa2f7f5-bc32-47a2-8904-32a4425a8791`. A second public preflight **PASSED** for staging identity, effective download disablement, MFA, closed authenticator enrolment, database readiness and security headers.

**Status:** Public staging runtime preflight PASS (owner reported). This is not a commercial sign-off. The two underlying release flags should also be independently confirmed as disabled with the newly added read-only `verify_staging_lockdown.py`, which reports only the flags' pass/fail verdicts and does not print the full Railway variable set. The newer lockdown deployment is separate from the prior deployment that was tested during Gate B.

Synthetic grant cleanup, provider-event review, object-storage permission verification, provider SSO revocation policy, audit retention and commercial risk acceptance remain pending.

## Owner-reported R2 and WorkOS security acceptance — 4 November 2026

The company owner states the independent WorkOS and Cloudflare R2 tests were
successfully completed and signed off. **Record this as owner-attested approval
of the WorkOS/R2 staging tests, not a new test independently performed by this
GitHub change.** No signed private report, provider exports, test identities
or storage URLs were requested for this repository. Keep them in access-
controlled organisational evidence storage, with reviewer name/role, dates,
control outcomes and report hashes available for the commercial audit.

Previously validated: staging Gate B operator report passed locally; after
reverting both test release variables to false, the public /health + /ready
preflight passed on staging deployment 6aa2f7f5-bc32-47a2-8904-32a4425a8791.

The latest owner workstation reported `verify_staging_lockdown.py`
`PENDING/FAIL: Cannot confirm Railway staging flags using read-only CLI`.
This is a **local CLI/JSON acquisition issue**; it does not override the
successful runtime /health security check. A Windows-compatible, read-only
piped-stdin mode was added so Railway CLI can execute under PowerShell and
provide JSON to the offline checker without printing secrets:

~~~powershell
cd C:\My_Applications\TCL-gateway-verification
git pull --ff-only origin feature/gateway-entitlement-approvals
railway variable list --service tcl-customer-gateway-staging --environment staging --json |
    python .\customer_gateway\verify_staging_lockdown.py --stdin
~~~

The CLI JSON can contain *all service variables including credentials*. Do
not show it in the terminal, save it to files, paste it into chat, or enable
PowerShell pipeline transcription while performing this sensitive check. The
Python utility prints **only** the two selected control flags and never
echoes the full JSON. This pipeline is **read-only** and never changes
provider configuration.

### Commercial gate still requires new decisions

Owner sign-off of staging security does not constitute approval to deploy
an unreviewed production WorkOS tenant, production R2 IAM, commercial
licensing/activation system, production Postgres, custom Cloudflare DNS or
customer marketing. The staging Python application deliberately requires
APP_ENV=staging; **do not simply change it to production**. The final
production candidate needs an explicit, peer-reviewed environment promotion
plan and new tests. Licensing must not be represented as automatic merely
because private downloads are now secured.

The R2 time-limited URL design permits previously minted GET bearer URLs
to remain valid until expiry despite grant revocation. Obtain an
explicit written owner commercial-risk decision about this up-to-300-second
window, or introduce an authorising proxy and retest before the first
real customer release.
