# TEC EPR Clinic Edition — final commercial release control sheet
**Prepared 4 November 2026 | Thueman Coke Limited / TEC Healthcare | NO PRODUCTION CUTOVER**

## Release intention

Market and distribute TEC EPR Clinic Edition through Thueman Coke Limited's
public software pages. New customer registration and contracts are managed
separately from the clinic's clinical EPR patient database. TEC Healthcare
retains control of licensing, installation-specific activation and clinical
support. TCL distributes private publisher-signed installers under an approved
intercompany agreement.

**Immutable prior candidate:** TEC EPR Clinic Edition 1.0.0, originally
reported 329,965,422 bytes, SHA-256
`E1C75BB867627CB60F0F5FF9737B602661550A15DF75F5DF52BF8C43835C8C0E`.
No work in this GitHub PR modifies, repacks or re-signs that archive.
Publisher RSA-4096 signing identity and verification are distinct from
any private **customer licence** signing key.

## Evidence and status as of 4 November 2026

| Area | Evidence status | Commercial disposition |
| --- | --- | --- |
| Signed software archive readback | Operator-reported A3 integrity PASS | Preserve immutable release |
| WorkOS authentication/MFA and R2 private GET | Owner reports independently tested and owner-signed; private supporting report not reviewed in GitHub | Owner-accepted staging UAT; retain protected original evidence |
| Entitlement grant/revocation/tenant isolation | 15 owner-confirmed checks, offline evidence consistency PASS | UAT reported complete |
| Staging lockdown | Owner disabled both download/release switches; public HTTPS/DB/MFA preflight PASS | Effective public staging download gating verified |
| Separate Railway variable verification | Local subprocess failed to fetch JSON; Windows piped JSON mode implemented | Owner should run read-only stdin command |
| Gateway CI (Python SQL, CodeQL and dependencies) | PASS on 4 Nov 2026 | Source-only assurance |
| TEC EPR **customer licensing policy** | Backend source review found an unconditional `Admin` role bypass of all licensed modules and `LICENSE_DISABLE=1` environment bypass | **BLOCKER pending signed-package validation and mitigation** |
| Production deployment | Gateway `from_environment` refuses non-staging, WorkOS production tenant/DB/DNS not provisioned/approved here | **NOT DEPLOYABLE AS-IS** |
| Commerce and offline licence issuance | Website customer interest is not a licence or purchase; owner signing/renewal/billing workflow remains incomplete | **BLOCKER before real sales** |
| Privacy, agreements, support and rollout | Commercial contracts/terms, pricing, data protection, support SLA, backups and customer onboarding approval still required | **BLOCKER** |

## Licence-policy security finding — separate source-only remediation

In GitHub repository `tlcoke2/tec_epr_backend`, current `main`
`src/middleware/checkLicense.js` allows every database-authenticated
customer `Admin` to bypass all 25 licensed route gates. It also permits
`LICENSE_DISABLE=1` to bypass licensing for everyone. Existing unit tests
explicitly codified the Admin bypass.

A **draft, not merged** source fix has been opened at:
`https://github.com/tlcoke2/tec_epr_backend/pull/20`.
It preserves the verified owner Superadmin bypass, requires valid module
subscriptions for ordinary Admin accounts, fails closed for the retired
global environment bypass and adds regression tests across all 25 routes.

Before commercial distribution, inspect the actual immutable 1.0.0 binary
against the tested source. The code in main **might differ** from what
was packaged. **Do not claim the already signed 1.0.0 archive has this
vulnerability until its contents are verified.** If affected, assemble a
separate versioned, newly signed release from reviewed, pinned sources,
perform customer clean-install + rollback, clinical regression, licensing
smoke, independent scanner, Medical Director acceptance and publisher
signing. Never overwrite or relabel the original signed 1.0.0.

## Commercial authorisation sequence

1. **Staging close-out.** Record the owner-signed WorkOS/R2 report reference
   and attestation date in a restricted internal register, verify both
   staging flags individually disabled, revoke/expire any remaining
   synthetic approved grant, and preserve the 15-check evidence.
2. **TEC license integrity.** Review the backend draft PR and existing
   production-candidate installer policy; ensure only owner Superadmin has
   the intended bypass and customer Admin cannot circumvent subscriptions.
   Complete clinical, installer, offline expiry and renewal regression.
3. **Offline licence issuance.** Define canonical license payload,
   customer/clinic installation binding, exact modules, trial start/end,
   grace/renewal policy, update and transfer rules, revocation support,
   cryptographic verification and key custody. Use an owner-approved
   offline signing workflow; do not embed private signing keys in Railway,
   GitHub Pages, shared CRM, browser JavaScript or software download.
4. **Commercial control plane.** Create a dedicated production gateway
   PostgreSQL, production WorkOS configuration, production MFA/recovery,
   strict per-customer entitlements and audit retention; maintain
   separation from the website CRM and EPR clinical databases.
5. **Delivery and website.** Publish public product/interest information
   separately from the private R2 archive. Use a reviewed, verified
   customer domain, exact identity-provider redirect allowlist,
   no customer JWTs or presigned URLs in GitHub Pages; preserve public
   gateway feature flag OFF until approved.
6. **Commercial agreements.** Execute TEC Healthcare↔TCL distribution/
   licensing/support rights, EULA, data-protection addendum, privacy
   transparency, billing/refund terms, installation fee/subscription
   prices, SLA, security incident policy and customer exit/backup terms.
7. **Operational resilience.** Verify encrypted independent backup/
   restore on the dedicated commercial DB; log retention, monitoring,
   secret rotation, customer support escalation, abuse/WAF controls,
   rate limits and release signing/change control.
8. **Production candidate proof.** In a **new** non-patient production-like
   environment, inspect the release image digests, verify two-admin MFA,
   isolation, withdrawal and expiration, verify license issuance/renewal/
   denial. A site connection and successful login **do not** prove
   commercial activation or clinical safety.
9. **Formal go/no-go.** TEC Medical Director accepts any new signed
   clinical release; the authorised TCL/TEC owner accepts pricing,
   insurance/commercial obligations and residual R2 bearer-link risk.
   Document independent reviewer, dates, private evidence location,
   remediation/accepted risks and rollback owner.
10. **Controlled first pilot.** One contracted site only; enable production
    configuration via reviewed PR and explicit change window. After pilot
    acceptance, extend marketing, licensed installs and billing to
    other customers.

## Mandatory production safety rules

- Staging PR #38 and website PR #39 remain drafts until formal final review.
- Never set `APP_ENV=production` on the current staging-guarded source
  and expect it to create a safe production service.
- Do not make the R2 bucket public. A grant revocation cannot revoke
  already-issued signed GET bearer links until expiry (<=300 seconds);
  explicit owner risk acceptance or proxy redesign is required.
- Never upload publisher/license private keys, evidence customer IDs, R2
  signed GET query parameters, patient records or secrets to GitHub/CRM.
- No real customer download entitlement should silently create a clinical
  software licence, payment or production patient tenant.
- A separate production database, provider credentials, HTTPS domain,
  backup procedure and rollback decision are mandatory.

## Approved next technical work (source-only)

- Windows-safe staging variable verification using the fixed piped JSON
  utility without exposing the full Railway variable list.
- TEC backend security PR #20 licence-policy review and exact release
  binary comparison.
- Production gateway design and operator sign-off of hosting, WorkOS
  production tenant, audit retention, R2 read-only credential scope,
  availability and abuse limits.
- Offline license signing *interoperability contract* based on the actual
  TEC EPR consumer format, then an isolated trial activation and renewal
  test; do not ship an invented incompatible license schema.

**Gate C = PENDING.** Staging security owner approval is acknowledged;
real commercial distribution and production activation require the
above source, licensing and operating controls.
