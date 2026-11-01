# MFA step-up staging validation

Target only TCL project `6f7f7da9-a02a-47ba-bf11-701e5866a949`, staging
`bb8c97db-c146-4c0e-b2fa-919b8aa38050`, gateway service
`71cc8a41-9fcc-41ef-806e-4642b015d8ac`. Database must remain the dedicated
`Postgres-A7e0` reference in COMMERCIAL_DATABASE_URL.

## What changes

An authenticated user can request a fresh WorkOS TOTP challenge. The gateway
selects the existing factor from that user's provider endpoint; the browser
cannot choose a subject, factor, challenge or role. A successful provider response
must match both stored challenge and factor IDs. Only then is an elevation saved,
with an audit event, for at most five minutes and no longer than the local session.
The account page displays the user's own WorkOS ID so operator identities can be
verified later. No administrator or tenant membership is created.

Both POSTs require exact same-origin and a session CSRF token. Forms have a bounded
body size. Challenges are consumed before verification; invalid codes need a new
challenge. Five starts per subject per ten-minute window limits retries across
sessions/replicas. Provider failure also consumes quota. The adapter never retains
TOTP secrets or codes. Gateway access logs remain disabled. Impersonated WorkOS
logins are refused. Missing/malformed evidence or provider failure denies elevation.

## Deployment order

1. Use a clean checkout of the reviewed PR #38 commit. Keep the existing checkout
   and the signed clinical release unchanged.
2. Set `GATEWAY_MFA_ENABLED=false` on the staging gateway. Deploy only its
   `customer_gateway` directory with `--path-as-root` to the exact IDs above.
3. Confirm `/health` returns staging, downloadsEnabled false, mfaStepUpEnabled false.
4. SSH to this gateway service. Run once:

   `GATEWAY_MIGRATE_ACCESS=add-access-tables-staging python migrate_access.py`

   Expected: eight empty access/MFA tables added, existing authentication records
   preserved. This uses a transaction and advisory lock. It refuses a database
   without exactly the expected existing authentication tables, unknown tables or
   an existing/partial access schema. If refused, inspect; do not reset or drop.
5. Exit SSH, set `GATEWAY_MFA_ENABLED=true` on the staging gateway, and wait for the
   deployment to succeed. `/ready` now checks all access tables as well as sessions.
6. In the browser, sign in, select **Verify authenticator**, and enter a fresh code.
   Expected account text: **Additional verification: verified for this session**.
   Administrator and download access must remain unavailable. Never send the code,
   authenticator QR, recovery codes or API key in chat.
7. Confirm logout blocks the account and previously opened verification form.
   Record successful live adapter validation separately from synthetic CI results.

If a check fails, set GATEWAY_MFA_ENABLED=false and redeploy. Existing sign-in stays
available; do not remove the additive tables or restore production databases.
The previous reviewed gateway commit can also be redeployed if necessary.

## Evidence and limits

36 local tests pass. CI runs the same suite on SQLite and isolated PostgreSQL 18.
Provider calls are mocked in automated tests; the live acceptance above is still
required. Successful MFA proves access to an enrolled factor, not business approval,
an administrator appointment, a licence, or an independent second reviewer.

Admin bootstrap, membership UI, grant approval routes, R2 signing, provider session
revocation integration, operational audit retention and concurrency/load testing
remain separate work. No production merge or release authorization is implied.

Provider API references checked 1 November 2026:
- https://workos.com/docs/reference/authkit/mfa
- https://workos.com/docs/reference/mfa/challenge
