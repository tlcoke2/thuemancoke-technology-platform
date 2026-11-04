# TCL customer gateway — staging candidate

This isolated staging-only service supports WorkOS AuthKit sign-in, appointed
administrators with MFA, two-person entitlement review, customer onboarding and
conditionally gated private R2 release links. It is **not production-authorised**,
does not issue software licences, and never imports the existing CRM or clinical
database code. See CUSTOMER_ROLLOUT.md and RELEASE_READBACK_REVOCATION.md.

## Server-side flow

- Fixed WorkOS AuthKit authorize/exchange endpoints, authorization code + S256 PKCE.
- Ten-minute random state tied to a separate secure browser cookie. State is hashed
  in PostgreSQL and atomically consumed on callback. PKCE verifier is server-side.
- Successful HTTPS back-channel exchange must return a verified user. No browser
  JWT or supplied identity/role is accepted. This is OAuth/AuthKit, not a general
  OIDC ID-token validator; no JWT parsing shortcut is used.
- Fifteen-minute opaque local session; only its SHA-256 is stored. Tokens from
  WorkOS are discarded, not persisted or sent to the browser. No silent refresh.
- Secure, HttpOnly, host-only SameSite=Lax cookies; session rotation on login;
  strict origin and synchronizer-CSRF checks on POST logout. Logout revokes only
  the local session, NOT the WorkOS SSO session. The UI says this explicitly.
- A login session and its minimal audit event commit together. Audit failure does
  not issue a session. Audit contains provider subject, event and timestamp only.
- Public UI does not display email/name. Logs do not include callbacks or tokens;
  Uvicorn access logs disabled. Configure proxy/observability query redaction too.
- Downloads are disabled unless both release flags are enabled and the signed-in
  customer has an active, approved, current entitlement. Sign-in alone grants
  no download permission. First administrator appointment remains an explicit
  staging procedure; no automatic customer administrator bootstrap occurs.

## Configuration (new isolated Railway service and new database)

Use project bountiful-curiosity / staging; service name tcl-customer-gateway-staging.
Provision a NEW Postgres service for this gateway. Do not reference Postgres-QQXu,
the production CRM database or either TEC clinical database.

Required variables:

| Name | Value |
| --- | --- |
| APP_ENV | staging (other environments refused) |
| WORKOS_CLIENT_ID | client_01M6AMEDVB2A0A64RRZ01YNAAH |
| WORKOS_API_KEY | Staging secret, entered directly in Railway |
| COMMERCIAL_DATABASE_URL | Reference to NEW dedicated PostgreSQL DATABASE_URL |
| GATEWAY_ORIGIN | Exact generated HTTPS origin, without trailing slash |
| GATEWAY_AUTH_ENABLED | false until database and WorkOS setup complete |

WorkOS staging redirects, using that exact origin:

- Redirect URI: `https://GATEWAY-HOST/auth/callback`
- Initiate login URI: `https://GATEWAY-HOST/auth/login`
- Sign-out URI: `https://GATEWAY-HOST/`

No wildcard redirects. Hosted staging pages use the gateway origin for this
rehearsal; final customer marketing/frontend hosting remains GitHub Pages.

Deploy only the customer_gateway directory with --path-as-root. Docker runs as
an unprivileged user. /health is liveness and does not certify DB connectivity.
After the initial deployment, in a gateway SSH shell, initialize only the new
empty DB using `GATEWAY_INITIALIZE_DB=new-dedicated-staging python init_db.py`.
The initializer refuses nonempty databases. No startup migrations are performed.
Check /ready after initialization, then enable staging sign-in and test browser
login, account, logout and expiry. Never submit real patient data.

## Current evidence and outstanding release gates

The owner has reported passing staging sign-in, MFA, appointed administrator
and customer download. The **actual customer-downloaded 1.0.0 archive** passed
pinned SHA-256/size, trusted publisher RSA-SHA256 detached-manifest signature,
and complete signed-manifest payload binding (**442 signed files plus 3 signing
metadata files**). This is owner-reported read-only operator evidence; the
local evidence JSON remains on the operator workstation. GitHub CI runs on
SQLite and isolated PostgreSQL 18. These integrity checks do **not** validate
a commercial licence or live entitlement revocation.

**Next acceptance:** live synthetic staging grant revocation, cross-tenant
denial, and previously minted R2 signed GET URL expiry. See
[REVOCATION_STAGING_ACCEPTANCE.md](REVOCATION_STAGING_ACCEPTANCE.md).
Do not mistake mocked tests for proof of live provider/R2 behaviour.

Provider session revocation/webhooks, session refresh, idle limits, rate limits,
abuse quotas, protected audit retention/export, dependency review, verified R2
credential scope and production independent security review remain required.
The fifteen-minute local session does not immediately track provider revocation;
already-issued R2 bearer links survive grant revocation until their expiry.
This candidate must remain staging-only while these controls are unfinished.

Docs checked: https://workos.com/docs/authkit/vanilla/python and
https://workos.com/docs/reference/authkit/authentication (2026-11-01).

## MFA and entitlement candidate

See [MFA_STAGING.md](MFA_STAGING.md) for the feature-disabled deployment and explicit
additive migration. This supersedes the earlier statement that MFA has no implementation;
live WorkOS step-up acceptance, operator provisioning and download integration remain
outstanding. MFA verification alone never grants a role or entitlement.

## Customer onboarding and delivery candidate

See [CUSTOMER_ROLLOUT.md](CUSTOMER_ROLLOUT.md) for the implemented customer proposal,
independent approval, customer view and disabled private R2 signer, the new explicit
additive migration, 85-test evidence, and the remaining production gates. This
supersedes earlier implementation-status notes; no live completion is implied.

## Branded customer experience (November 2026)

See [UI_STAGING_ROLLOUT.md](UI_STAGING_ROLLOUT.md). Pages use a responsive,
same-origin stylesheet with no third-party scripts. Customer login landing,
account, MFA, onboarding, approval and download pages have been redesigned.
Logout redirects to a clear signed-out page. Browser errors are styled HTML,
rather than raw framework JSON; `/health` and `/ready` remain JSON for monitors.
The presentation update needs **no schema migration** and does not alter
entitlement policy, signing keys, flags or release contents.
