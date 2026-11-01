# Customer access controls: review candidate

This adds an internal database service and synthetic tests on top of gateway PR #37.
It does not change the deployed login flow, migrate a database, create real customer
access, or enable downloads. No new public endpoint is exposed.

## Implemented

- Separate tenant, membership, administrator, MFA elevation, download grant and
  entitlement event tables. These are separate from patient and CRM databases.
- Grant proposal requires an active session, active administrator, and a matching
  server-recorded MFA elevation, at most five minutes old.
- Approval requires another active administrator with recent MFA. Approval also
  rechecks the tenant, proposing administrator and expiry.
- Release identity is restricted to the verified Clinic Edition 1.0.0 release.
- Contract and approval references are mandatory. These references are records,
  not automated proof of a legally valid contract.
- Pending/approved/revoked transitions use transactions and PostgreSQL row locks.
  Approval and revocation retries do not duplicate audit events.
- Audit insertion failure rolls back the corresponding grant mutation.
- No method accepts a browser-supplied role or MFA boolean. No method provisions
  an administrator, membership or MFA elevation.

## Validation

Run `python -m unittest discover -s customer_gateway/tests -v`.
The existing GitHub workflow runs this suite against SQLite and isolated PostgreSQL
18. Local SQLite: 20 tests pass (12 authentication and 8 entitlement tests).
PostgreSQL concurrency races and production operations are not certified by these
unit tests. Audit records are append-only in these service methods, not immutable
against a database owner; external protected audit retention is still required.

## Required integration before enabling access

1. Connect verified WorkOS MFA evidence to short-lived elevations, bound to the
   current opaque session and provider subject. A configured MFA requirement or
   verified email alone must not create an elevation. SSO users are exempt from
   WorkOS hosted MFA policy; do not silently accept SSO as proof of MFA.
2. Establish two independently authenticated operator identities and controlled,
   audited bootstrap. Separate usernames do not themselves prove two people.
3. Add a reviewed additive migration against the dedicated staging commercial
   database; preserve the three existing authentication tables. Do not rerun
   `init_db.py` against the initialized database.
4. Add authenticated, same-origin/CSRF-protected administration routes and UI,
   input limits, rate limits and audited membership changes. Tenant membership
   is not granted by login or by an email-domain match.
5. Integrate the authorization policy from PR #36 with freshly loaded membership,
   grant and release state. Add a read-only R2 signer and audit issuance before
   returning a short-lived URL. Keep download issuance disabled until these pass.
6. Test tenant isolation, concurrent approval/revocation, provider outage,
   revocation and restore in the isolated environment. Complete independent review.

## Release decisions still outstanding

Approved price/tax and contract terms; privacy retention and operator roles;
trial/licence approval and offline signing procedure; renewal/support lifecycle;
independent review and formal production authorization. No payment or licence
issuance is implemented by this change. The signed clinical master stays unchanged.
