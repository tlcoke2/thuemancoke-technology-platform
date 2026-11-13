# TEC EPR 1.0.1 customer gateway — production readiness and deployment
**Status: NOT DEPLOYED. Draft production cutover procedure; downloads and release switches OFF.**
**Prepared 13 Nov 2026. Scope: new 1.0.1 clinic installations ONLY.**

## What is already implemented — reuse, do not rebuild

- The owner confirmed a *live staging* Railway gateway with WorkOS AuthKit login, PKCE/state, TOTP enrollment + MFA step-up, authenticated customer sessions, separate-appointed two-administrator customer onboarding/review, audit trails, tenant-scoped entitlements, revocation, and private Cloudflare R2 presigned GET (maximum 300 seconds).
- Staging host: `tcl-customer-gateway-staging-staging.up.railway.app`. Staging owner-attested 15/15 entitlement/revocation checks are locally self-consistent. These are **not proof of a production deployment** or independent provider-level security review.
- Staging project UUID: `6f7f7da9-a02a-47ba-bf11-701e5866a949`, staging environment `bb8c97db-c146-4c0e-b2fa-919b8aa38050`, existing staging gateway service `71cc8a41-9fcc-41ef-806e-4642b015d8ac`. **Never target these staging service/environment identifiers for a production action.**
- Owner reported signed and independently verified 1.0.1 archive of **286145967 bytes**, SHA256 **`18c0450e9bb3562889fa1c8b0be233840aebe4dd81b37541540b793012f66aed`**, published/read back in the **private** bucket `tec-epr-private-releases`. The owner holds the non-secret gateway handoff at `C:\Users\tlcok\TEC-EPR-1.0.1-FRESH-RELEASE-OWNER\PRIVATE-GATEWAY-101-ACTIVATION-HANDOFF.json`.
- 1.0.1 publisher SPKI SHA256 `b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a`; historical 1.0.0 verifier `6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`. Version 1.0.0 remains quarantined for downloads.

## Critical distinction: staging != commercial production

The original gateway staging service is a successful functional baseline to **reuse**. It does not establish that a production-specific Railway service, separate PostgreSQL, production WorkOS client/API credentials and redirect allowlist, dedicated private hostname, Cloudflare records or a distinct owner-approved production release have been provisioned. DO NOT copy the staging database or provider secrets to the production tenant. The stage `PR #38` is draft; the 1.0.1 gateway `PR #40` is stacked on #38 and is also draft. Do not merge to main or enable downloads as a side effect of source review.

## 13 November production Railway inventory — owner CLI verified

Owner's actual `railway status`, `railway environment list` and `railway service list --environment production` show **two existing production services, neither the customer gateway**:

| Environment/service | Existing resource | Guard |
| --- | --- | --- |
| `staging`, service `tcl-customer-gateway-staging` | Online, EU West, service `71cc8a41-9fcc-41ef-806e-4642b015d8ac`, separate staging DBs `Postgres-A7e0`, `Postgres-QQXu` | REUSE for staging comparison only; NEVER switch to production or migrate its DB. |
| `production`, service `thuemancoke-technology-platform` | Existing public API `https://api.thuemancokelimited.com`, service `1987f0cf-3572-4618-8e70-5ee5dfe41132` | DO NOT deploy customer gateway files or set gateway WorkOS variables on this API. |
| `production`, database service `Postgres` | Online, PostgreSQL 18, service `6044eb89-238f-497f-b1b9-469dc13695fc`, persistent production volume | Treat as ALREADY USED/UNVERIFIED ownership; NEVER repurpose, reset, migrate or connect the new gateway without an independent owner DB isolation assessment. |
| `production`, `tcl-customer-gateway-production` | **NOT LISTED** | Dedicated new gateway app service still needs provisioning; do not claim it already exists. |
| `production`, gateway-specific PostgreSQL | **NOT LISTED** | New, empty, dedicated gateway database must be provisioned separately. |

This is an operator-provided CLI inventory, not access to Railway management APIs. It does not prove ownership of the existing production `Postgres` service; treat it as protected and reserved. **The production environment already exists. Do not create another Railway environment.** Create only an additional gateway app service and dedicated DB inside the existing `production` environment after owner review. No existing service, Postgres volume or deployment has been changed by this inventory.

## Railway source configuration (13 November owner build error)

A newly attempted service was configured with GitHub branch `main` and root `/customer-gateway` (hyphen). This path does **not** exist on `main`: the reviewed gateway lives under `customer_gateway` (underscore), on `release/tec-epr-101-fresh-private-gateway-20261111` (PR #40, stacked on the staging gateway PR #38). Railway `service list --environment production` did not yet show the new service; check the production canvas for an unapplied/pending change or a service created in another environment before creating anything again.

For the **new dedicated gateway service only**, use Railway Settings → Source: repo `tlcoke2/thuemancoke-technology-platform`, branch `release/tec-epr-101-fresh-private-gateway-20261111`; Settings → Root Directory: exactly `/customer_gateway`; Settings → Build: Dockerfile auto-detected as `Dockerfile` at the service root. Do not point to `/customer-gateway` or use the repo-root `main` branch. The root's `Dockerfile` copies files relative to `customer_gateway`, so applying a repo-level Dockerfile with wrong context can break COPY statements. Until an immutable reviewed release is merged and approved for production, treat this branch deployment as **pre-activation production candidate** only: set `GATEWAY_DOWNLOADS_ENABLED=false`, `GATEWAY_RELEASE_APPROVED=false`; do not configure any real customer grant or expose the login link. Either disable automatic deploys or require manual approvals/pinned commits.

Note that a successful **build** is not a successful production startup: `from_environment()` explicitly refuses startup without a dedicated commercial database and an approved production WorkOS client/MFA and origin. Do not bypass those checks, reuse CRM Postgres or staging WorkOS keys, or modify the currently online public API service. Record real service ID and verify `railway service list --environment production` now includes the new service before doing any database initialization.

## Owner-side single-command automation available (13 November 2026)

A reviewed Node.js owner-run provisioning utility is prepared for the already-authenticated Windows Railway CLI: `TCL-Gateway-Production-Autoprovision.cjs`, local SHA-256 `309666ceea595ad2f56df985347c2b658029fb3e12bdccdc2f1613945d96ce35`. Its command is `node TCL-Gateway-Production-Autoprovision.cjs --provision` after verifying the SHA. A fully mocked local CLI regression exercised service list parsing, safe create, separate PostgreSQL provisioning, app-only download-deny variables, correct source branch and `/customer_gateway` root; **it has not been run against the owner's Railway account**. The utility is supplied to the owner as a chat attachment, not installed into production. It uses an isolated Railway CLI link and checks exact TCL project ID and `production` environment before mutations; preserves the existing production API and `Postgres`, creates a new named customer gateway service if absent and a distinct new PostgreSQL service, and records the new DB service name locally. It does not copy staging WorkOS credentials or clinical databases, inspect secrets, generate approval references, deploy software manually, initialize production tables, or enable downloads.

After provisioning, the gateway can **remain offline** because production WorkOS/HTTPS domain and separate schema approvals are intentionally not automatically generated. The owner/Work operator must finish those provider-specific approvals using authenticated Railway, WorkOS and Cloudflare provider consoles, then perform isolated production DB bootstrap and smoke gates P2–P5. Do not bypass `APP_ENV=production` and the existing fail-closed `from_environment` checks to make a partially configured service report healthy. New production Postgres provisioning can incur Railway charges.

## Gate P0 — private infrastructure inventory (read only)

From the existing authenticated Windows terminal:
```powershell
railway list
railway status
railway environment list
railway service list --environment production
```
The `railway status` command describes the **currently linked environment**, normally staging in the original tools folder. Confirm the production service and a **separate** production database from the Railway UI before taking any action. Do not paste `railway variable list --json` output; it can contain credentials. If a production service already exists, **reuse it** and audit its deployment/source instead of creating duplicates.

## Gate P1 — isolated production provisioning (owner-run in Railway)

1. In the existing authorised TCL project, select the **production** environment (or an independently named equivalent), and create a *new* service for the customer gateway if no appropriate existing one exists (suggested name `tcl-customer-gateway`). Do **not** promote the existing staging service or duplicate its database into production.
2. Provision a separate new private Railway PostgreSQL instance for the gateway only. Do not use the TCL CRM, legacy `Postgres-A7e0` staging gateway database or any TEC EPR clinical DB. Use a dedicated least-privileged DB account. Configure Railway-managed backups and an independent encrypted restore/recovery check before live customer records.
3. Configure a gateway-specific HTTPS subdomain of `thuemancokelimited.com` (proposed `customers.thuemancokelimited.com`, **not asserted to exist**). In the production Railway service Settings → Networking → Custom Domain, use the exact supplied CNAME **and verification TXT** records in Cloudflare, then confirm TLS valid and routing; don't invent DNS targets.
4. In WorkOS, create/verify the **production** AuthKit environment/client and secret; separately allowlist the *exact* `https://<production-gateway-host>/auth/callback` redirect. Keep the existing tested staging configuration unchanged. Confirm live login and actual TOTP step-up with approved real operator identities using the production client, without exporting provider tokens or MFA codes. Operator accounts must be appointed through a separate audited two-person process; staging accounts/roles must not be copied.
5. Add **production service scoped** private Railway variables (no credentials in GitHub, CLI command history or chat):

| Variable | Pre-activation setting / purpose |
| --- | --- |
| `APP_ENV` | `production` |
| `GATEWAY_ORIGIN` | Exact final HTTPS gateway origin |
| `WORKOS_CLIENT_ID`, `WORKOS_API_KEY` | Distinct production WorkOS client and secret |
| `COMMERCIAL_DATABASE_URL` | Dedicated gateway production Postgres private DSN only |
| `GATEWAY_AUTH_ENABLED`, `GATEWAY_MFA_ENABLED` | `true` after production WorkOS validation |
| `GATEWAY_ONBOARDING_ENABLED` | `false` until two-person role/approval checks finish |
| `GATEWAY_ENROLLMENT_SUBJECTS` | empty by default |
| `GATEWAY_DOWNLOADS_ENABLED` | `false` |
| `GATEWAY_RELEASE_APPROVED` | `false` |
| `GATEWAY_PRODUCTION_LAUNCH_APPROVED` | `true` only with real owner-approved production-service deployment |
| `GATEWAY_PRODUCTION_DATABASE_APPROVAL_REF` | Real >12-character dedicated DB owner-reviewed reference |
| `GATEWAY_PRODUCTION_WORKOS_APPROVAL_REF` | Real >12-character production WorkOS/redirect approval reference |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Dedicated *read-only* private bucket R2 service credentials (can remain absent with downloads OFF) |

6. Use the reviewed `customer_gateway/Dockerfile`, which now **includes** `release_101_config.py` needed for controlled activation and `init_production.py` for empty-DB bootstrap. Pin deployment to reviewed/merged source, including underlying PR #38; do not deploy a random local checkout or set build root to the repository root. Before release activation, review the container's dependency scan and provenance.

## Gate P2 — one-time EMPTY production schema, never run on staging

On a **new, empty**, dedicated production database only, use the reviewed `init_production.py`, which refuses any existing table/view/materialized view, requires explicit owner authorisation, and creates all required authentication, MFA/access and customer onboarding tables in one transaction.

Additional one-time bootstrap-only environment variables:
- `GATEWAY_INITIALIZE_DB=new-dedicated-production`
- `GATEWAY_PRODUCTION_BOOTSTRAP_APPROVAL_REF=<real-dated-owner-record>`
- `GATEWAY_EXPECTED_NEW_DATABASE_NAME=<exact-private-DSN-database-name>`

Keep both download flags explicitly `false`, and enrolment allowlist empty. Run once on the exact targeted **new production gateway** using Railway SSH after reviewing the target IDs:
```powershell
railway ssh --project 6f7f7da9-a02a-47ba-bf11-701e5866a949 --environment production --service tcl-customer-gateway -- python init_production.py
```
After PASS, **remove** the three temporary bootstrap authorisation variables and restart/redeploy the gateway. Do NOT rerun against existing populated DB. On failure, inspect and preserve schema/transaction logs; do not reset live data, force-migrate or drop tables.

## Gate P3 — production smoke, downloads still OFF

- `GET /health` returns `environment: production`, `downloadsEnabled: false`, `mfaStepUpEnabled: true`; `GET /ready` passes against the new production DB.
- WorkOS production sign-in, callback with PKCE and state, authenticator start/verify, logout/revocation, cookie/CSRF/HTTPS/security headers all pass.
- Two **independently appointed** production administrators with fresh MFA can propose/approve a synthetic test customer. Same-person approval fails; unapproved/other tenant cannot access the grant. Abort if anything issues a link while either release flag is OFF.
- Confirm source deployment commit and Docker image, separate DB, R2 read-only credential scope and zero real clinical patient data. Confirm provider-session policy, audit retention/exports, backup+recovery, rate limits, abuse monitoring and legal/terms requirements.
- Perform independent security review of all outstanding B1-B12 controls in `INDEPENDENT_SECURITY_REVIEW.md`. Specifically record maximum 300-second already-issued bearer URL revocation exposure and whether owner accepts it.

## Gate P4 — authenticated 1.0.1 activation, separate audited change

After real medical and owner production approval, use the owner-generated `PRIVATE-GATEWAY-101-ACTIVATION-HANDOFF.json` values through **private** Railway variables only (not screenshots/chat/source). Required evidence keys include:
`GATEWAY_RELEASE_ID`, `GATEWAY_SIGNED_101_RELEASE_EVIDENCE_JSON`,
`GATEWAY_VERIFIED_101_REPORT_JSON`, `GATEWAY_R2_101_EXPECTED_ETAG`,
`GATEWAY_R2_101_READBACK_SHA256`, `GATEWAY_MEDICAL_RELEASE_APPROVAL_REF`,
`GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF`.

With both release/download flags STILL `false`, confirm private R2 object HEAD using read-only scoped credentials, independently verify 1.0.1 signer and complete digest, and check an unauthorised synthetic GET is refused. Then in an approved change window set the two explicit production flags to `true` and verify a **single** separately approved customer grant, cross-tenant denial and revocation. Restore both flags to `false` immediately for any unexpected result.

**Never expose release archives via GitHub Pages or a public R2 bucket.** Activate the public TCL website gated customer login CTA only after successful gateway production deployment and accepted pilot.

## Gate P5 — go/no-go evidence

Record real Railway project/environment/service/deployment IDs, production HTTPS hostname, WorkOS production application **ID only** (never secrets), DB owner reference, CI SHA/results, 1.0.1 release hash and private R2 readback metadata, independent B1–B12 signoffs, clinical approval, commercial owner approval, TTL/revocation residual-risk acceptance, rollback owner and backup restore proof. Keep the evidence private and tamper-evident.

**Current disposition: SIGNED_R2_PRIVATE_READY / WORKOS_STAGING_ACCEPTED / GATEWAY_PRODUCTION_NOT_YET_EVIDENCED / DOWNLOADS_OFF.**
