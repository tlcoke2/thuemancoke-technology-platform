# First staging administrator appointment

MFA login acceptance is complete according to the owner for both nominated users.
This change adds a controlled first appointment command and approval dashboard.
It does not change the TEC EPR application administrator or superadmin accounts.

## Preconditions and authorization

Use only the dedicated TCL customer gateway in staging. The owner must nominate
both identities and the second person's verified email. First-time enrollment must
be closed (`GATEWAY_ENROLLMENT_SUBJECTS` empty). Do not put WORKOS_API_KEY in a
command line or share its value; the script reads the existing service environment.

Deploy the reviewed branch's customer_gateway directory to staging, then run via
Railway SSH on the customer gateway service:

```sh
GATEWAY_APPOINT_ADMINS=confirmed-staging-pair python appoint_admins.py \
  --owner-id USER_ID_FROM_OWNER_ACCOUNT \
  --approver-id USER_ID_FROM_SECOND_ACCOUNT \
  --approver-email NOMINATED_SECOND_APPROVER_EMAIL
```

Both provider identities are fetched server-side from WorkOS. Verified emails are
required; the second email must match the nomination and the two addresses must
differ. Both users need an existing successful gateway MFA audit event. Their old
five-minute elevation need not still be active for appointment; each subsequent
administrative action requires a fresh active elevation and session.

The command inserts exactly two active administrator records and two appointment
audit events in one transaction, serialized with a PostgreSQL advisory lock. It
refuses other, partial, disabled or conflicting appointments. Repeating the exact
already-audited pair is a no-op. It cannot reset credentials, reactivate a revoked
administrator, create tenants/grants, change patient data or issue a licence.

Expected result:

`PASS: Both staging administrators appointed and audited.`

## Browser acceptance

Each person signs in independently, selects Verify authenticator and confirms a
fresh code. Their account page should show **Gateway administrator / approver**
and **Open approval dashboard**. The dashboard requires current MFA; when elevation
expires it directs them back to their account for verification.

An empty dashboard is expected until approved synthetic grant fixtures exist.
Displayed grants include tenant, release, proposer, validity interval, contract
and approval references. Administrators can approve another operator's pending
grant or revoke a grant. Server checks reject self-approval even if a request is
constructed manually. All POSTs require exact Origin and the session CSRF token.

Do not seed real customer grants merely to test this screen. Customer membership
onboarding/proposal UI, private R2 signing and live entitlement acceptance remain
separate tasks. No download URL or licence is issued by this update.

## Validation and rollback

52 tests cover sign-in, enrollment, verification, migration, appointment and grant
controls. Appointment tests include wrong email, unverified identities, missing
MFA evidence, disabled/partial existing roles, provider failure, idempotence and
audit rollback. Dashboard tests cover missing role, expired MFA, CSRF, self-approval,
HTML escaping and approval/revocation. CI runs SQLite and isolated PostgreSQL 18.
Live WorkOS appointment lookup and browser acceptance remain operator checks.

No new migration is required. Roll back application code if necessary; preserve
appointment/audit records for review. No destructive rollback or automatic role
removal is provided. Production and clinical systems remain outside this command.
