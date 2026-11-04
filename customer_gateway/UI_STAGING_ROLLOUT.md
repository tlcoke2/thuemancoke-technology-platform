# Branded gateway UI — staging acceptance

This update is **presentation-only** for customer sign-in, account, MFA,
administrator review, customer entitlements, signed-out recovery, download
handoff and human-readable form errors. It does **not** change the underlying
WorkOS PKCE flow, permissions, memberships, licence rules, or signed installer.

## Implementation and boundaries

- `ui.py` supplies a responsive, script-free design, accessible navigation,
  keyboard focus styles, readable mobile layouts, and local CSS.
- `/assets/gateway.css` is same-origin, and CSP explicitly permits only
  same-origin styles; no JavaScript, third-party CSS, tracking, or analytics.
- Sign-in starts on `/` and continues to the existing WorkOS AuthKit redirect.
  `/account` is a signed-in dashboard; `/customer` lists approved access only.
- `POST /auth/logout` still enforces origin + CSRF and atomically revokes the
  local session with an audit. It now redirects (303) to `/signed-out`, which
  explains that the WorkOS SSO session may remain active.
- User-facing 400/401/403/404/405/413/415/422/503 errors now render a safe
  HTML recovery view, with the HTTP status preserved. Unexpected server
  exceptions never print exception text. Monitoring probes `/health` and
  `/ready` continue to return JSON by design.
- The post-authorisation download page displays the expiring private link and
  pinned SHA-256, with no-store and no-referrer headers preserved. URLs remain
  short-lived bearer credentials and **are never stored or logged** by the UI.
- CSS does not grant new entitlements or release approval. Forms retain their
  existing CSRF, recent administrator MFA, tenant isolation and rate checks.

## Safe deployment

1. Review and confirm that GitHub Actions on the new PR #38 head pass for
   **both SQLite and PostgreSQL 18**. Leave the PR as draft.
2. Deploy the reviewed `customer_gateway/` directory **only** to the existing
   TCL gateway staging service and its dedicated PostgreSQL database. Build
   from the updated Dockerfile, which packages `ui.py`.
   Avoid any clinical, CRM or signer-master deployment targets.
3. Keep `APP_ENV=staging`. Do not run `init_db.py`, repeat additive migrations,
   or modify WorkOS identities, bucket grants or production configuration.
4. Preserve approved staging controls from the current deployment. Do **not**
   enable either release/download feature flag solely to test this UI.
5. Smoke test the anonymous `/` landing, HTTPS CSS at
   `/assets/gateway.css`, WorkOS sign-in, customer account, MFA and
   administrator approval. Check mobile layout and keyboard navigation.
6. Sign out using the **form button**, confirm HTTP 303 to `/signed-out`
   and that the old gateway session can no longer access `/account`.
   A page-open `GET /auth/logout` must show a styled 405, not end a session.
7. Test an expired session (401), denied action (403), unknown page (404)
   and invalid form (400/422). Their content type should be HTML, with
   useful return links. `/health` and `/ready` intentionally stay JSON.
8. Only during a separately approved staging entitlement test, verify the
   customer download page contains the requested link, expires in at most five
   minutes, and does not leak URL query strings into audit or access logs.
   Do not publish screenshots of signed URLs or cookies.

## Rollback

Keep the gateway on the isolated staging service. If user acceptance fails,
redeploy its previously known-good reviewed gateway image/commit and retain
existing database schema, audit events and customer approvals. No new schema
migration is required for these presentation changes.

## Cryptographic release gate — still separate

The owner has confirmed full SHA-256 and byte-size agreement on the customer
download. The published release's **detached manifest signature is not yet
independently verified**, and controlled live revocation tests remain pending.
Do not treat styling/UX sign-off as production release authorization.
