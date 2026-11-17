# TEC EPR subscription billing integration

## Verified account changes, 17 November 2026

The approved account is `acct_1TgB8dK17IwlxhlL` (live). The three approved monthly
JMD Prices and Product IDs are recorded in `customer_gateway/commercial_catalog.json`.
All are tax exclusive. No Checkout Session, live subscription or charge was created
by this integration work. Invoice previews do not create payable invoices.

The owner previously confirmed UK VAT and Jamaica GCT registrations. The existing
UK VAT registration was recorded in Stripe as `taxreg_1UcvPlK17IwlxhlLXpxAAgtv`.
The subsequent preview `upcoming_in_1UcvQ7K17IwlxhlLsshKTwQm` returned
`standard_rated`, subtotal JMD 25,000, tax JMD 5,000, total JMD 30,000 for a UK
customer address. This is a configuration check, not a legal opinion or tax filing.
The VAT number was not supplied; add the seller's actual tax identity to Stripe's
business/invoice settings after verifying it with the owner/accountant.

**Unresolved:** the preview identifies account country **US**, whereas the seller
is the UK company. Tax head-office settings do not change the account's legal
country or merchant contract. Confirm the account's verified legal business with
Stripe before accepting payments for Thueman Coke Limited. Do not change the
account country programmatically or assume an address update fixes this.

Jamaica does not appear in the Stripe Tax supported-country table or this API's
registration options at this review. No GCT rate, registration or proxy country
was invented. Agree the supported/manual collection route and tax treatment with
the owner/accountant before Jamaica checkout is enabled. Software implementation
services require their own classification and seller/scope. They are not silently
charged as additional software licences. Perpetual purchases and large Enterprise
orders remain private quotations.

## Customer journey and security boundaries

Website → `/start` → verified WorkOS account → `/customer/billing` or private
request → hosted Stripe Checkout → signed webhook reconciliation → existing
independent download approval → customer installation → protected offline issuer.

`/account` and the requests page link to subscriptions. No payment card details
pass through the gateway. A success-page visit never records a payment.
`/customer/billing/portal` maps only the signed-in subject's stored customer ID.
Pinned portal configuration `bpc_1UcvXqK17IwlxhlLkoQVKzvg` allows payment-method
updates, invoice history and cancellation at the billing period end. Plan changes
and public portal login links are disabled.

The webhook path is `/api/webhooks/stripe`. Subscribe to the exact `EVENTS` tuple
in `customer_gateway/billing.py`, pinned API version `2026-10-28.endive`.
It verifies signatures over raw bounded request bytes with a five-minute replay
window, enforces live/sandbox separation, atomically records processed event IDs,
serializes duplicate deliveries and retries temporary provider/mapping failures.
It uses Stripe resource relationships, not emails or untrusted metadata, to map
subscription and risk events to local orders. Current provider state is fetched
under a row lock to reconcile out-of-order delivery. A subscription is shown as
active only after the current invoice is paid. Refund/dispute/fraud events create
a sticky review hold, which later renewal events cannot silently remove.
Any partial refund requires review; it is not automatically treated as harmless.
Unrelated account transactions are acknowledged without changing TEC orders.

Risk holds block new private downloads. A cancelled/unpaid latest subscription
also blocks new downloads. Existing offline licences and already downloaded files
cannot be remotely recalled by this ledger. Existing R2 links retain their short
expiry. The ledger never modifies clinical records, invents licence claims or
bypasses the two-person access-approval process. `/admin/billing` requires the
existing appointed administrator and recent MFA.

## Deployment and secrets

New code is safe to deploy with billing disabled (the default). Existing identity,
downloads and requests remain available. No schema migration runs at startup.

Only the dedicated commercial database may be migrated. In the production
gateway's Railway console, set `GATEWAY_MIGRATE_BILLING=add-billing-ledger-production`
for the migration process and run `python migrate_billing.py` with billing off.
The script pins Railway service/environment and database/host, checks the actual
connected server and adds only `gateway_billing_orders` and `gateway_billing_events`.
It refuses unrelated tables or changed schemas and is repeatable. Never run
`init_production.py` on the populated database. Never reset or delete volumes.

The ChatGPT Stripe connection does **not** supply a runtime API credential to the
Railway application. A dedicated restricted API key must be entered directly in
Railway, never in chat, GitHub, customer downloads or this document. Required API
access: read current account, Products/Prices, Checkout Sessions, Subscriptions,
Invoices, Invoice Payments and Charges; create Checkout Sessions and Billing
Portal Sessions. If Stripe's permission model groups these operations, choose the
narrowest available role and verify it in an isolated sandbox. Do not grant key
management, balance/payout/transfer, arbitrary customer deletion or account admin.

Variables for each separate environment:

| Variable | Purpose |
| --- | --- |
| `STRIPE_RESTRICTED_KEY` | Dedicated `rk_test_…` sandbox or `rk_live_…` production key |
| `STRIPE_WEBHOOK_SECRET` | That environment's endpoint signing secret (`whsec_…`) |
| `STRIPE_EXPECTED_ACCOUNT` | Exact account ID for that environment |
| `STRIPE_LIVEMODE` | `false` in sandbox; `true` only in production |
| `STRIPE_PORTAL_CONFIGURATION` | Pinned portal configuration for that environment |
| `STRIPE_SANDBOX_CATALOG_JSON` | Sandbox-only map from each plan code to `product`/`price` IDs; amounts stay fixed in the catalogue |
| `GATEWAY_BILLING_ACCEPTANCE_VERIFIED` | `true` only after recorded sandbox and business/tax acceptance |
| `GATEWAY_BILLING_ENABLED` | Keep `false` until migration, secret setup, acceptance and rollback checks pass |

Configure a separate Stripe sandbox and isolated gateway/database. Create matching
sandbox Products and monthly Prices (the live IDs do not work in a sandbox).
Use `clinic_essentials`, `professional`, `enterprise` as map keys. For example the
JSON shape is `{"clinic_essentials":{"product":"prod_…","price":"price_…"},…}`;
all three entries are required. Never copy live keys/data into the sandbox.

After configuration, verify a successful test payment, failed payment, async
payment success/failure, cancellation, renewal, duplicate delivery, renewal before
checkout delivery, refund, dispute and fraud warning. Verify the customer sees
only their own records and cannot select arbitrary Prices or customer IDs.
Confirm no licence or access grant is created by payment alone. Check the signed
webhook delivery is HTTP 200 and the order is reconciled, not just redirected.
Record real evidence and then run production checks with no real customer charge.

## Rollback

Set `GATEWAY_BILLING_ENABLED=false` to close new checkout and management. Keep
Stripe retry behavior in mind: the disabled webhook returns 503 until restored;
replay missed deliveries after recovery. Do not drop the ledger or alter previous
commercial approvals. Existing clinical installations remain separate.

## Sources

- https://docs.stripe.com/billing/subscriptions/webhooks
- https://docs.stripe.com/api/checkout/sessions/create
- https://docs.stripe.com/tax/supported-countries
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/keys-best-practices

This document records implemented controls and unresolved activation requirements.
It is not HIPAA/GDPR certification or regulatory approval of a medical device.
