# Customer onboarding and private delivery candidate

## Completed implementation

- Administrator-only customer proposals bind organisation, verified WorkOS subject
  and email, UTC validity dates, contract/pilot reference and review reference.
- Proposals create inactive tenants/memberships and pending grants. Repeated form
  submissions with the same identifier and payload are idempotent; rebinding is refused.
- A distinct active administrator with fresh MFA must approve. WorkOS identity/email
  is rechecked. Tenant, membership, grant and audit activate in one transaction.
- Existing approve/revoke controls integrate with onboarding. A revoked pending
  request cannot activate. There is no arbitrary browser-supplied role or tenant grant.
- /customer lists only the signed-in subject's active memberships and their grants.
- Private GET issuance rechecks local session, tenant, membership, grant, validity,
  release controls and administrator MFA. Both new release flags default false.
- The R2 signer is pinned to the verified Clinic Edition 1.0.0 bucket/key, endpoint,
  byte count and recorded ETag. It performs bounded HEAD change detection before
  signing. Only GET is signed; expiry is at most five minutes and bounded by grant
  and session expiry. Size/ETag are not cryptographic signature verification.
- An issuance audit must commit before a URL is returned. URLs and storage credentials
  are not saved to the audit. No-store/no-referrer responses protect delivery pages.
  There is a per-subject, per-grant limit of ten issuances in fifteen minutes.

## Deployment sequence (staging only)

Use the dedicated TCL gateway service, not the store API or clinical services:
project 6f7f7da9-a02a-47ba-bf11-701e5866a949,
environment bb8c97db-c146-4c0e-b2fa-919b8aa38050,
service 71cc8a41-9fcc-41ef-806e-4642b015d8ac.

1. Deploy the reviewed commit's customer_gateway directory with
   GATEWAY_ONBOARDING_ENABLED=false, GATEWAY_DOWNLOADS_ENABLED=false,
   GATEWAY_RELEASE_APPROVED=false, GATEWAY_ENROLLMENT_SUBJECTS empty.
   Keep the successful MFA configuration enabled.
2. Confirm the administrator appointment command from ADMIN_APPOINTMENT.md has
   succeeded. It is safe to repeat for the exact same audited pair; it will not
   replace, reactivate or add different administrators.
3. In Railway SSH, run once:

   `GATEWAY_MIGRATE_ONBOARDING=add-customer-requests-staging python migrate_onboarding.py`

   This adds only gateway_customer_requests and preserves authentication, MFA,
   administrators and previous audit rows. It refuses unrelated or already-migrated
   schemas. Never rerun init_db.py or migrate_access.py on this initialized database.
4. Set GATEWAY_ONBOARDING_ENABLED=true, wait for deployment and verify /ready.
   Downloads and release approval must remain false.
5. Owner signs in, verifies MFA and opens Approval dashboard -> Customer onboarding
   and review. Use a synthetic organisation, a controlled customer's actual verified
   WorkOS ID/email, explicit future expiry, and clearly labelled synthetic references.
   No patient data and no real contract approval should be fabricated.
6. Owner submits; own approval is refused. Elizabeth signs in separately, verifies
   MFA and reviews identity, organisation, dates and evidence before approving.
   The customer's /customer page then lists approved access. Another account must
   not see that tenant. Revoke and confirm the grant is displayed as revoked.

## Private-download configuration (prepare, do not activate yet)

Provision a separate R2 S3 credential scoped to Object Read only on
tec-epr-private-releases. Do not reuse a publisher upload credential. Add only via
Railway's private variables UI:

- R2_ACCESS_KEY_ID
- R2_SECRET_ACCESS_KEY

Neither credential belongs in GitHub, browser code, commands copied into chat or
screenshots. The endpoint and release object are pinned in code; no DNS change,
public bucket, custom bucket domain or new upload is needed.

Live signing requires deliberate staging authorization plus
GATEWAY_DOWNLOADS_ENABLED=true and GATEWAY_RELEASE_APPROVED=true. Do not set these
until membership/approval/revocation UAT, private bucket/read credential scope,
release custody/retention and independent review are accepted. A synthetic grant
must not become a real entitlement by accident. No payment or licence is issued.

When authorized, validate one controlled customer's signed download, byte count,
full SHA-256, detached signature with an independently authenticated publisher key,
expiry, rejection of a different customer and refusal after revocation. Never paste
signed URLs into chat or logs. Already-issued bearer URLs remain usable until their
short expiry; revocation stops new issuance, not an existing URL immediately.

## Evidence and known limits

90 local tests pass. The inherited workflow runs the same suite against SQLite and
isolated PostgreSQL 18. Automated WorkOS/storage operations are mocked except local
SDK signature generation; no private cloud object was fetched by these tests.
The separate commercial_core policy from PR #36 is reused in download_policy.py
and its nine policy tests are included in the gateway suite.

Provider-session revocation integration remains incomplete: local sessions expire
at fifteen minutes; privilege checks and download decisions use current local state.
The release approval flag changes through deployment, not an instantaneous distributed
withdrawal transaction. Existing signed links are bearer credentials. Approval/grant
and database concurrency/load testing, protected audit retention and recovery, publisher
key publication/trust distribution, and independent review remain rollout gates.

Production remains prohibited by from_environment's staging guard. Customer billing,
renewal/support workflows, offline licence approval/signing, approved prices/terms,
privacy retention, full production operations and formal release authorization are
not completed by this candidate. The signed clinical master remains untouched.

## Rollback

Disable onboarding and both download/release flags, then redeploy the previously
reviewed gateway image/commit if necessary. Preserve the additive request table and
all audit records for review; no destructive rollback is needed.

## Read-only storage connection check

After adding the separate bucket-scoped Object Read credentials privately in Railway,
keep both download/release controls false and redeploy this candidate. In the gateway
SSH shell run `python check_private_storage.py`. This performs only HEAD on the pinned
release object and reports size/ETag agreement without printing credentials or signed
URLs. It does not modify the database or cloud settings. An operator must separately
confirm credential scope and disabled bucket public access. Do not replace the existing
full-hash/signature evidence with this metadata check.

Administrator forms now explain the five-minute verification window and provide a
second-tab verification link. Expired onboarding submissions return an HTML recovery
page with no write. Download issuance also rechecks MFA after the storage HEAD call.
