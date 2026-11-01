# Private download gateway: implementation boundary

Status: authorization core only, NOT a deployable or authenticated customer portal.
No endpoint, migration, R2 signer, public link, licence generation or CRM change
is introduced by this component. No new runtime dependencies are required.

## Verified distribution evidence (owner-reported, 31 October 2026 local time)

- Archive SHA-256: e1c75bb867627cb60f0f5ff9737b602661550a15df75f5df52bf8c43835c8c0e
- R2 bucket: tec-epr-private-releases; public development URL disabled, no custom domain.
- Key: tec-epr/clinic-edition/1.0.0/TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz
- Length: 329965422 bytes.
- Owner confirmed download of stored bytes, expected SHA-256, external public-key
  fingerprint and detached manifest signature. Backend, frontend and database image
  IDs matched the owner-held clinical acceptance record before transfer.
- Owner confirmed written TEC/TCL storage and distribution authority is on file.
- These are reported checks, not independent clinical or legal certification.
- Source master remains unchanged on owner Windows host. Preserve separate encrypted backup.

## Policy implemented

Every request must have a trusted authenticated issuer/subject, verified email,
active tenant membership, approved unexpired grant, recorded approval and contract,
and an available pinned release. Admins require MFA and receive no tenant bypass.
The decision's maximum lifetime is 300 seconds, shortened to the remaining grant
or session lifetime. Rejected inputs produce no URL or storage operation.

Principal booleans and grant records are trusted adapter inputs, NOT authentication.
Do not bind these dataclasses directly to an API request or use CRM_ADMIN_KEY.
The opaque release ID resolves server-side; callers cannot supply a bucket or key.

## Integration still required before a downloadable link can be issued

1. Dedicated commercial PostgreSQL database, migrations reviewed separately.
   Persist issuer/subject membership, approval/contract references, release status,
   grants and audit events; do not copy clinical or production CRM data.
2. OIDC provider configuration and verified server-side authentication. Validate
   issuer, signature, audience, expiry, nonce/state and authorized algorithms;
   require provider-validated MFA for administrators and verified email. Use
   secure HTTP-only sessions with CSRF protection and exact origin policy.
3. Every download request reads fresh membership, grant and release state from
   the commercial database. Public enquiry submission cannot approve a grant.
   Separate approval actions require an audit trail and two-person review where
   required by the licence approval policy.
4. Transactionally record the download authorization and its unique request ID
   before generating or returning a URL. If audit persistence fails, return no URL.
   Prevent stale grants/races during authorization, and rate-limit request issuance.
5. R2 signer uses a read-only token scoped to this bucket, only GET for the pinned
   object, and the decision TTL. Never put publisher or licence signing keys here.
   Return Cache-Control: no-store; redact URL query signatures from all logs.
6. Presigned URLs are bearer links, not intrinsically single-use or tied to a
   recipient after issuance. Revoking a grant stops future issuance; existing
   URLs may remain valid until expiry. Do not claim immediate link revocation.
7. Audit events distinguish authorization/link issuance from a completed download.
   Test OIDC failure, CSRF, two-tenant isolation, audit outage, revoked/expired grants,
   replay/idempotency, rate limiting and real private R2 read-back on staging.

## Remaining operator configuration

Select/confirm an OIDC tenant and staging application, including issuer, audience,
redirect URI and admin MFA policy. Provide public configuration identifiers only;
store client secrets and read-only R2 credentials directly in the isolated service.
Customer support, retention, contract/pricing and production signoff remain separate.

Run: `python -m unittest discover -s commercial_core/tests -v`
