# TEC EPR customer centre — engineering and operations guide
Version 1 · 17 November 2026 · Implemented scope and remaining work

## Architecture and separation
The public website is the React/Vite frontend on GitHub Pages. The software page links to the Railway customer gateway at https://customers.thuemancokelimited.com/start. WorkOS handles sign-up, email verification and credentials. The gateway accepts only verified server-exchanged identities, creates a short-lived server-side session and keeps business requests in its commercial PostgreSQL database. Patient records remain in the separately installed EPR. Cloudflare R2 retains private signed releases. Licence signing remains on the owner's protected computer.

## How this change was created
1. Read the actual deployed gateway branch, release/licence-final-publication; do not assume main is the Railway source.
2. Inspect the main website source and Pages deployment workflow.
3. Add a visible Customer portal navigation link and replace the obsolete software enquiry form with the customer centre.
4. Add GET /start and the WorkOS sign-up screen hint while retaining PKCE, state, verified email and existing callback validation.
5. Add authenticated GET/POST /customer/requests. Identity comes from the server session, not form fields.
6. Add a private request table with an idempotent submission identifier, bounded fields, five requests per identity per 24 hours and a PostgreSQL transaction lock per identity.
7. Enforce origin and CSRF validation, escape submitted text and isolate customer request listings by subject.
8. Add /admin/software-requests, restricted to appointed administrators with recent MFA.
9. Create only the additive gateway_self_service_requests table and its subject index in tcl_customer_gateway. No volume, database, existing table or row is removed.
10. Run the targeted Python suite and frontend production build before publishing. Verify the deployed page and startup.

## Daily operation
Customers register, verify their email, sign in and choose demo, subscription enquiry, outright quotation or installation licence request. The receipt appears in My software requests. Administrators open the software request inbox from the approval dashboard and verify the customer, terms and intended use. Existing two-person onboarding and grant controls continue to govern private downloads.

A request remains received until an operator processes it using the existing approval workflow. This first release does not automatically change request status, email a receipt, charge a customer, issue a licence or activate a tenant. Do not describe it as complete unattended commerce.

## Commercial routes
Published subscription prices are implementation plus monthly fees, not perpetual licence prices. Owner chose private quotation for outright purchases. No new price, tax rate, refund promise or EULA has been invented. Before unattended subscriptions: connect authenticated checkout to approved Stripe price IDs, calculate applicable tax, validate signed webhooks, handle duplicates, failed payments, refunds and cancellations, reconcile entitlements and test the full lifecycle in test mode.

## Licence signing boundary
Publisher signing authenticates the software archive. Licence signing authorises a particular installation. They use different keys. Never upload the owner's private keys to the website, customer portal, source repository or customer package. A future automation service needs a separately protected signer, bounded approved products/modules/terms, idempotent issuance, a durable ledger, revocation policy and backup/rotation procedures. The existing desktop issuer remains the operational issuance path.

## Security and operations
Verified controls: server-side identity exchange and email verification; secure HttpOnly SameSite cookies; CSRF and exact origin checks; HTML escaping; short-lived private download URLs; grant and tenant checks; recent administrator MFA; bounded commercial requests; no patient-file upload endpoint in this change.

Not established by these changes: absence of exploitable vulnerabilities, complete penetration-test coverage, Cloudflare WAF/bot configuration, DDoS capacity, endpoint protection of customer PCs, all-vendor contractual compliance, or clinical safety certification. AI-assisted attacks use the same underlying attack surfaces; retain layered controls rather than a claim of being unhackable.

Operator checks: review access and request logs, patch dependencies, alert on login and request spikes, test backup restores, maintain separate emergency access, restrict R2 credentials to necessary objects, rotate keys after suspected exposure, and document incident actions. Set a documented business-request retention period and run authorised retention procedures; do not silently delete requests.

## Deployment and rollback
Website: main triggers .github/workflows/deploy-pages.yml. Gateway: release/licence-final-publication auto-deploys to its dedicated production Railway service. Preserve the exact final archive, manifest and verification evidence. Roll back source through a reviewed forward commit or previous known-good deployment; do not sync/delete project resources or reset volumes. The new empty/additive table may remain during rollback.

## Acceptance still required
A new real account must complete WorkOS sign-up and verification, submit its first request, view only its own requests and later obtain an approved download. Use synthetic business details for QA. Payment and automatic licence issuance need separate acceptance evidence. Existing signed software binaries were not changed by this website work.
