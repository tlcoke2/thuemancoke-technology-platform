# Customer access controls: review candidate

This adds an internal database service and synthetic tests on top of gateway PR #37.
The MFA step-up candidate adds protected verification routes behind
`GATEWAY_MFA_ENABLED=false` by default. It does not create administrator/customer
access or enable downloads. An explicit additive staging migration is included;
it never runs automatically. See MFA_STAGING.md for the staged rollout.

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
18. Local SQLite: 52 tests pass (authentication, entitlement, MFA and migration cases).
PostgreSQL concurrency races and production operations are not certified by these
unit tests. Audit records are append-only in these service methods, not immutable
against a database owner; external protected audit retention is still required.

## Required integration before enabling access

1. Validate the implemented WorkOS challenge/verification adapter with the actual
   staging account. The provider must confirm the single-use challenge and factor
   identity before elevation. Hosted MFA settings alone do not create elevations.
   SSO without an enrolled TOTP factor is denied step-up. First-factor enrollment
   is restricted to operator-listed subjects; no reset endpoint is exposed.
2. Run the explicit appoint_admins.py staging command for the owner-authorized
   pair, after closing first-time enrollment. It checks live provider identities,
   the nominated approver email and gateway MFA audit evidence. Separate usernames
   do not themselves prove two people. Live appointment acceptance is still required.
3. Review and run the additive migrate_access.py command only on the dedicated
   staging commercial database with the feature disabled. It preserves existing
   authentication tables, refuses unknown/partial schemas and refuses repeats.
   Do not rerun init_db.py against the initialized database.
4. Validate the added MFA-protected approval dashboard and approve/revoke routes
   with the appointed pair. Customer intake/proposal screens, rate limits and
   audited membership changes remain. Tenant membership is not granted by login
   or by an email-domain match.
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
