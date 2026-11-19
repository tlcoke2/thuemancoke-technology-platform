# Customer payment options

The owner explicitly selected the existing account acct_1TgB8dK17IwlxhlL for continued integration. This does not assert that Stripe has enabled payments. Its current readback remains country US, business type individual, charges_enabled=false, payouts_enabled=false and requirements.past_due.

The public /payments page shows the approved JMD monthly and separate implementation prices. Each plan offers a payment-link request recorded against the verified customer's account. The existing CSRF, origin, per-subject limit, idempotency, private export and appointed/MFA administrator review apply. No schema migration is required. A request is not a generated or delivered payment link.

When runtime billing is enabled and Stripe permits charges, the customer billing page offers hosted Stripe Checkout. No raw card fields are collected by the website or gateway. Checkout checks the selected account's charges_enabled flag as well as its account ID and pinned price. Existing signed webhook reconciliation remains required. Payment-link requests remain available while checkout is closed. Never represent a request as a completed payment or an issued licence.

The website pricing cards link to /payments and plan-specific requests. After registering/signing in, customers use My software requests to submit and track their request. Operators review these in /admin/software-requests.

Remaining: Stripe account verification, runtime restricted API key and endpoint signing secret, real sandbox acceptance and supported Jamaica GCT/implementation-service handling. No live payments, cards, verification documents, customer messages or payment links were created by this UI change.
