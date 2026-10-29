# Thueman Coke Limited — Enterprise Software Store & TEC EPR Commercial Launch
**29 October 2026 | Controlled development | NO automatic production deployment**

## Platform architecture — existing services first
- **Public marketing and software interest**: `www.thuemancokelimited.com/software.html` (GitHub Pages static Vite site), with privacy and optional marketing-consent controls.
- **Intake API and business CRM**: Railway-hosted FastAPI at `api.thuemancokelimited.com`. `/api/software/interest` adds **one software-interest record and one existing sales CRM lead in a single database transaction**. Public requests never create an application user, an EPR licence, a payment, or a patient database.
- **Private commercial control plane (next separate service)**: customer identities, commercial orders, contracts, invoice state, subscription schedule, support plans, access grants, trial approvals, notification outbox, audited manual approval and business data. **Do not** put private clinical data or licence signing keys in this database.
- **Private release object storage**: Cloudflare R2 or a separately approved equivalent (non-public bucket), versioned objects and retention, signed-file manifests, cross-region off-site copy and restricted object-store credentials. Static GitHub Pages is for web assets and marketing only—**not** 1.0.0 package storage. Avoid Railway ephemeral disk for durable files.
- **Customer auth**: externally managed OIDC with MFA for customer portal, with server-side issuer/audience/expiry/signature checks. Do not reuse the site's shared `CRM_ADMIN_KEY` as public customer authentication. TEC staff requires independent RBAC, separate admin access and audit.
- **Download service**: short-lived single-customer scoped grants; verify customer identity and entitlement server-side; issue private object-store signed URLs with short expiration; no unapproved public archive URL, no permanent token in frontend, complete audit, rate limiting, and revocation. A static web page must never contain bucket secrets or licence-signing keys.
- **Customer installation**: existing signed/verified EPR v1.0.0 package and separate offline RSA-signed installation-specific subscription, administered by TEC Healthcare. Each clinic owns a dedicated clinical PostgreSQL environment. No patient records ever flow into TCL CRM.

## v1.0.0 immutable release baseline
Original owner-reported signed archive (on owner's Windows machine only):
`C:\My_Applications\TEC-EPR-Commercial-Releases\TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz`

SHA-256:
`E1C75BB867627CB60F0F5FF9737B602661550A15DF75F5DF52BF8C43835C8C0E`

Trusted publisher public SPKI SHA-256:
`6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`

The archive has **not been uploaded or independently inspected** in this TCL repository. Never rebuild, rename as a different image, re-sign or mutate the original. Obtain a separate verified **distribution copy** from a controlled workstation, compare SHA-256 and detached signatures with the separately authenticated public key and inspect the release attestation before uploading. Do not distribute keys, `.env`, backups or patient data. **TEC Healthcare ownership, TCL distribution rights and support accountability must be evidenced in a signed intercompany agreement.**

## This branch — first verified development scope
- Public TEC EPR product profile with truthful feature limits, no unverified certification/AI/interop claims.
- Demo / controlled trial review / quotation requests with distinct marketing consent, privacy notice, honeypot and Cloudflare Turnstile validation.
- Production intake defaults to **OFF**. Activate only after data-protection/commercial signoff, WAF and source-level tests. If `APP_ENV=production`, **both** the Turnstile site key and secret must be set before the service accepts requests.
- New `software_interest_requests` SQLAlchemy table, created with existing startup `Base.metadata.create_all` (additive table only; does **not** modify existing patient, sales or CRM rows). **Plan an Alembic-managed, reviewed migration for later expansion**—do not use automatic schema changes for complex upgrades.
- CRM classified as `review`, zero estimated value, explicit human follow-up. Website neither sends automated marketing nor grants software.

## Production-safe rollout checklist
1. CI on the isolated feature branch must PASS. Pull request remains unmerged while functionality and privacy are reviewed.
2. Confirm cloud service snapshot/rollback, current PostgreSQL restore, existing CRM test lead isolation and current API health. The external website test was not accessible during the original analysis; browser/DNS/smoke test still required.
3. Set up Cloudflare Turnstile widget for both apex and www hosts; store **secret only** in Railway; site key may be exposed by `/api/software/registration-config`. Cloudflare WAF rate limit `POST /api/software/interest` and protect SMTP from abuse.
4. Review TCL/TEC roles, privacy notice, marketing opt-in text, marketing unsubscribe process, lawful basis, data retention and processors (Railway/Cloudflare), Jamaica OIC obligations, UK privacy if soliciting UK customers. The Jamaica OIC website displayed a temporary pause in registration on 29 Oct 2026; reconfirm official status.
5. Verify exact signed master *on separate owner-controlled machine* and place approved **distribution copy only** in non-public object storage, with release version, hash, image digests and customer restrictions. No public link, and no keys or customer databases.
6. Provide OIDC identity provider, customer portal, admin RBAC/MFA, release download service and offline licence issuing handoff. Do not treat trial requests as automatic entitlement approval.
7. Validate prod and staging CORS, response headers, WAF, content security, replay/abuse controls, database backup and rollback. E2E test with synthetic contacts and approval; verify leads appear in existing CRM without duplicates.
8. After audited go/no-go approval, merge approved PR, deploy Railway and GitHub Pages, and **only then** set `SOFTWARE_LEADS_ENABLED=true`. Do not alter production by simply testing this branch.
9. Use a single-site Jamaica pilot first. Publish SLA, EULA, DPA, operator privacy notice, user/admin/troubleshooting manuals and a clear export/exit process.

## Remaining commercial product work
| Module | Proposed service | Release gate |
| --- | --- | --- |
| Catalogue | searchable software/SKU/module/version/supported platform details | no direct public object URLs |
| Identity & registrations | email verification, customer account/OIDC MFA, requested facility & staff onboarding | verified lawful processing |
| Trial management | reviewed 14–45 day trial agreement and isolated synthetic evaluation | independent offline signed activation |
| Licence and renewals | installation registry, licence audit, eligibility, 45/15-day reminders | protected key custody; human second signoff |
| Payments | contract→invoice→payment reconciliation→licence approval | tax, settlement verification, idempotent payment callbacks |
| Downloads | R2 private version store, safe short-lived access grants, SHA256 + signed manifest verification | owner-supplied binary copy and public key |
| Support | case intake, P1–P4 SLA, customer-authorised remote session and RPO/RTO evidence | no patient information in tickets |
| Marketing | TEC-approved product claims, SEO, opted-in segmented communications, CRM conversion and reports | separate opt-in and unsubscribe |
| Administration | audited multi-entity TEC/TCL contract management with staff MFA | distinct roles and no PHI |
| International | jurisdiction-specific tax, privacy, medical-device intended-purpose and security evidence | separate legal signoff |

## Operational safeguards
- Never run `docker compose down -v`, `prisma migrate reset`, `prisma db push` or silent schema conversions on an EPR customer environment.
- No advertising a trial as self-service or instantly downloadable until the customer account/download and offline licence approval controls exist.
- Customer-controlled clinical data and administrative commercial contacts are separate legal/privacy purposes.
- Enabling software intake is a distinct operational act; it is intentionally disabled by default in Railway.
