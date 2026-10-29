# TCL software store — staging readiness audit, 29 October 2026

Scope: PR #30 only. Signed TEC EPR v1.0.0 master, clinical systems, production database and cloud settings unchanged.

## Observed baseline
- PR head before this follow-up: cc5b359daab3e08c84f38a2a4b6c0f21ab0fe2fb; base main: 8da152ad8605bc4ca209a8db6fff94933a94d13d. PR draft, unmerged.
- Marketplace and CodeQL workflows green on that head. Existing 9 backend tests used SQLite only; no independent approval present. Sourcery generated a review guide, which is not an approval.
- Public HTTP inspection: https://www.thuemancokelimited.com redirects 301 to https://thuemancokelimited.com/; apex returns 200, GitHub Pages response headers. Source CNAME matches apex. No DNS change required for this work.
- https://api.thuemancokelimited.com/api/health returned ok:true, environment:production. This establishes liveness only, not database backup health.
- Railway dashboard signed-in project listing opened. Subsequent UI interactions timed out twice; no settings, source branch, variables, volumes or backup policies could be verified. No Railway mutations attempted.

## Existing application behaviour (source review)
- Contact endpoint creates contact and sales lead transactionally, then attempts SMTP notification. SMTP host, SSL/STARTTLS, recipient and credentials are environment settings. Software interest does not send email.
- Existing CRM endpoints use shared X-Admin-Key/CRM_ADMIN_KEY. Do not reuse for customer accounts; OIDC/MFA service remains separate future work.
- CORS comes from ALLOWED_ORIGINS, permits Content-Type and X-Admin-Key, credentials false. Actual Railway allowlist still unverified.
- Cookie script records accept/decline in localStorage and exposes preference controls. Advertising page is informational. Consent UI alone does not establish compliant tracking or retention.
- Existing main module calls create_all and ensure_crm_columns at import; the latter can ALTER old CRM schemas and backfill NULL classification/archive values. Do not import/run against production as a read-only audit. Production migration/backup approval remains required even though the software-interest table is additive.
- No CSP appeared in the inspected apex response. Cloudflare WAF, CAPTCHA widget hostname/action configuration and backup retention remain unverified.

## Follow-up fixes
- All environments require configured CAPTCHA keys and allowed hosts; APP_ENV spelling or staging no longer bypasses verification.
- Malformed CAPTCHA responses fail closed; database failure logs omit SQL exception details that could expose applicant contact data.
- Isolated PostgreSQL CI added alongside SQLite. Test harness rejects non-loopback or non-test database targets and never inherits production DATABASE_URL.
- Added tests for transaction rollback and recovery, missing keys across environments, malformed email/unknown fields and provider timeout.
- Software form API origin is generated at build time from VITE_SOFTWARE_API_URL. Staging build refuses missing origin or the production API; only HTTPS origins without credentials/path/query are accepted. Both browser requests have bounded timeouts.

## Remaining gates before staging/production
1. Inspect exact Railway TCL service source, build root, deployment SHA and environment names read-only. Verify dated PostgreSQL backup and isolated restore evidence. No production migration authorised by this audit.
2. Independent code review on updated head, full CI including PostgreSQL and frontend staging-origin checks.
3. Create empty separate staging environment/database (never clone production data/secrets), use staging-only SMTP sink/no delivery credentials, separate CRM key, staging Turnstile host/action, SOFTWARE_LEADS_ENABLED=false initially. Build frontend with staging API and exact CORS origin. Enable synthetic intake only after controls verified.
4. Add/review abuse rate limits, request replay/idempotency, privacy retention/deletion process, CSP and staging end-to-end browser tests. Network timeouts must not prompt uncontrolled duplicate submissions.
5. Production rollback: retain deployment commit and environment-variable inventory without secrets in GitHub; disable SOFTWARE_LEADS_ENABLED, revert app deployments on failure, retain additive table/data. Any DB restore requires operator-approved plan and verified backup; never drop tables as rollback.
6. Owner/legal approvals, private R2 custody, OIDC/MFA and commercial lifecycle remain unimplemented. No claims of enterprise launch completion, clinical certification, authenticated download entitlement or payment readiness.

The owner archive hash and independent publisher fingerprint remain those in SOFTWARE_MARKETPLACE_LAUNCH.md. No archive requested, uploaded, rebuilt or signed in this audit.
