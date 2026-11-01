# TCL WorkOS staging sign-in service

Candidate only: a hosted sign-in rehearsal, not the production customer gateway.
No download signer, R2 credential, licence action, admin privilege or entitlement
is exposed. This service never imports the existing CRM application's DB code.

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
- Downloads return 403 even after login. No customer administrator bootstrap.

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

## Outstanding release gates

Real WorkOS browser flow remains untested until staging deployment. Eleven test
cases mock provider responses and test SQLite; CI also runs against PostgreSQL18.
Tests cover replay, cross-browser state, unverified email, provider failure,
session expiry, CSRF, audit rollback and no download/admin access.

Admin MFA must be established from provider-validated context before any privileged
endpoint exists. Provider session revocation/webhooks, session refresh, idle limits,
rate limits and abuse quotas, audit retention/export, full dependency audit, secure
customer membership/grant persistence and production review are still required.
The fixed short local session does not immediately follow provider-side revocation.
This candidate must remain staging-only while those controls are unfinished.

Docs checked: https://workos.com/docs/authkit/vanilla/python and
https://workos.com/docs/reference/authkit/authentication (2026-11-01).

## MFA and entitlement candidate

See [MFA_STAGING.md](MFA_STAGING.md) for the feature-disabled deployment and explicit
additive migration. This supersedes the earlier statement that MFA has no implementation;
live WorkOS step-up acceptance, operator provisioning and download integration remain
outstanding. MFA verification alone never grants a role or entitlement.
