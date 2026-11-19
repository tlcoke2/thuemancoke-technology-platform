# Customer centre operations — current implemented scope

See `TEC-EPR-NON-STRIPE-CLOSEOUT.md` for completed work and outstanding acceptance.
Customer routes: `/start`, `/payments`, `/customer/requests`, `/customer/billing`,
`/customer` and `/help`. Public installation help and a downloadable guide are now
available at `/help/customer-guide.txt`.

The appointed administrator completes recent MFA in `/account`, reviews private
requests at `/admin/software-requests` and uses protected status forms. Received,
reviewing and awaiting-customer are workflow states; closed/rejected do not grant
access. Separate existing two-person approvals govern downloads. Private request
exports at `/customer/requests/export` contain only the signed-in identity's
commercial requests, not patient records or the identity provider's full data.

Payment-link requests are recorded and tracked; no automatic link issuance or
email receipt is asserted. Hosted checkout and signed billing/risk reconciliation
are implemented but remain disabled pending the documented activation checks.
`/admin/billing` is also restricted to appointed operators with recent MFA.

Customers install the signed archive into a new folder, use Subscription to
export installation JSON, and submit an installation licence request. The web
form does not accept that JSON file. The agreed support channel and protected
owner-side issuer are still required. No private key enters the gateway.

Website deployments use main. Railway customer gateway uses
release/licence-final-publication, root customer_gateway. Keep these distinct.
Never reinitialise a populated gateway database or reset a recovered volume.
Roll back through a known-good source/deployment; keep additive ledger tables.

The immutable signed clinical archive was not rebuilt or changed. Public help,
source tests and passive HTTP checks do not certify HIPAA/GDPR compliance,
clinical safety, medical-device applicability, WAF configuration or recovery
readiness. Preserve actual independent and per-site acceptance evidence.
