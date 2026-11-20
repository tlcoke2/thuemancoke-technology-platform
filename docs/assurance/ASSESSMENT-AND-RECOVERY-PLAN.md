# Non-Stripe assessment and recovery execution plan

Applies to the final licence-enabled 1.0.1 archive, manifest `cd66121ca8df`.
This plan supplies work packages; execution evidence is recorded separately.

## Independent security assessment

Owner-authorised scope proposed for the assessor: TCL customer gateway, public
software/signup pages, the exact signed clinic installation in an isolated lab,
and the owner-side licence issuance boundary. Confirm third-party hosting rules
and a test window before active testing. No denial-of-service, credential stuffing,
real patient data, destructive database tests or access to unrelated tenants.

Provide two synthetic customer tenants, appointed MFA operator/approver accounts,
revoked/expired entitlements and an isolated installed clinic with distinct
facilities. Agree assessor identity/independence, secure report delivery and
emergency stop contacts. Test:

1. Registration, verified-email enforcement, PKCE/state/callback integrity,
   session fixation/expiry/logout/revocation and recent MFA enforcement.
2. Cross-tenant object references, facility boundaries, role changes, direct API
   calls, approval separation and customer/administrator exports.
3. CSRF, stored/reflected injection, upload validation, redirect abuse, rate limits,
   browser security headers and exposure of secrets in errors/logs.
4. Private R2 object access, link lifetime, revoked grants, signature/key pinning,
   altered archive/licence, replay, wrong installation and expired licence.
5. Licence issuance job tampering, duplicate delivery, worker restart, ledger
   recovery, private-key access and operator/key separation.
6. Deployment/dependency/provenance review. Retest findings on exact corrected
   revisions; retain original and retest reports with scope and limitations.

Deliver severity, reproducible synthetic steps, affected revisions, remediation,
retest and residual-risk decision. Source tests and this plan are not the report.

## Clinical and regulatory work package

Use CLINICAL-AND-PRIVACY-WORKBOOK.md and the module manual. A qualified clinical
safety owner must review intended use, operating context, hazards, mitigations and
residual risk. Assess wrong patient/facility, incorrect result/unit/reference
interval, prescribing errors, currency/auto-billing, missed tasks, downtime,
licence expiry and external AI. Preserve linkage from hazard to test evidence.

The clinical reviewer should reconcile the earlier medical-director document with
the final source/image changes. Determine which evidence remains applicable and
which changed workflows need delta review. Obtain actual role acceptance and
site-specific training decisions; existing permission to develop is not replaced.

A regulatory adviser must assess intended purpose and country-specific status,
particularly AI/decision support, prescribing and laboratory instrument interfaces.
Do not advertise worldwide medical approval. NHS DCB0129/0160 requirements depend
on supply/deployment context; software-device classification depends on purpose
and functionality. Disable or restrict unapproved optional workflows at the site.

Primary references reviewed:
- https://digital.nhs.uk/services/clinical-safety/clinical-risk-management-standards
- https://www.gov.uk/government/publications/software-and-artificial-intelligence-ai-as-a-medical-device/software-and-artificial-intelligence-ai-as-a-medical-device
- https://www.gov.uk/government/publications/crafting-an-intended-purpose-in-the-context-of-software-as-a-medical-device-samd

## Privacy and legal work package

For Thueman Coke Limited (32 Vivian Gardens, Watford WD19 4PG, UK) and each
customer, identify controller/processor roles for clinic data, portal contacts,
payments, support, backups, logs and optional AI. Document lawful basis and the
applicable health-data condition, minimisation, retention, access requests,
incident notification, subprocessors and international transfers. Complete the
actual DPIA and unresolved risks with the privacy owner. Agree DPA, support access,
trial/EULA, perpetual licence scope, renewal, refund, support and termination terms.
Do not promise indefinite updates or unrestricted clinical use by implication.

Assess HIPAA covered-entity/business-associate applicability and BAAs where
required; product encryption alone is insufficient. For Jamaica, establish the
applicable OIC registration and data-protection duties for the deploying controller,
including Healthy Concept Medical Centre. Registration is evidence to obtain,
not an assertion that it has already been completed.

Primary references:
- https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/guide-to-accountability-and-governance/data-protection-impact-assessments/
- https://www.hhs.gov/hipaa/for-professionals/security/guidance/guidance-risk-analysis/index.html
- https://oic.gov.jm/register-of-data-controllers
- https://oic.gov.jm/content/what-are-obligations-data-controllers

## Cloudflare verification

`collect-cloudflare.py` prompts locally for a zone-scoped read-only token and uses
GET requests only. Minimum permissions depend on the requested endpoints: Zone
Read, Zone Settings Read and appropriate Zone WAF/Rulesets Read. Never supply
write permissions for this collector. Do not paste tokens into chat. Execute:

```
python scripts/assurance/collect-cloudflare.py --zone YOUR_ZONE_ID --output cloudflare-readback.json
```

The output contains zone status, selected TLS/HTTPS settings and a ruleset
inventory. Failures remain unverified. An inventory is insufficient to prove that
rules are enabled, linked or effective. An authorised operator must additionally
inspect rule detail and exceptions, bot/rate-limit modes, proxy/origin protection,
log retention and delivery of a real test alert. Confirm that legitimate signup,
MFA, callbacks and downloads still function. Store account evidence privately.

References:
https://developers.cloudflare.com/api/resources/rulesets/methods/list/
https://developers.cloudflare.com/ruleset-engine/rulesets-api/view/
https://developers.cloudflare.com/fundamentals/api/reference/permissions/

## Isolated recovery acceptance

The retained Railway recovery volume is not a test target. Never detach, reset,
initialise or overwrite it for this exercise. Use an encrypted off-host backup
and a disposable, isolated environment without production network access.

1. Record approved RPO/RTO, backup identity/time, encrypted off-host location,
   schema/version, release hashes and responsible operator.
2. Verify encryption/key availability under a controlled recovery account. Verify
   Windows host device encryption, patching and endpoint protection separately.
   Do not export recovery keys, environment files, patient rows or passwords.
3. Start an isolated disposable restoration. Use the documented database major
   version and restore procedure; prevent accidental production connections.
4. Check schema, record counts, representative synthetic records, relationships,
   attachments and licence identity. Confirm anonymous and cross-facility denial.
5. Measure time to usable service and latest recoverable transaction time; compare
   with the agreed RTO/RPO. Exercise paper downtime reconciliation and staff roles.
6. Record pass/fail and defects; securely dispose of the isolated restored data
   under the retention policy. Preserve backup, report hashes and reviewer decision.

This Linux authoring environment cannot verify the customer's Windows encryption
or execute their off-host restoration. Earlier DR approval must be scope-matched
and current-site evidence recorded before this item is closed.

## Protected automatic licence issuance

The existing local encrypted-key manual issuer remains the working production
boundary. Do not place its private key in Railway, R2, the website or a package.

Implement automation as a separate protected local signer with a narrowly scoped
queue. A job must contain an authenticated approval reference, unique request ID,
installation UUID, approved organisation, explicit modules, UTC expiry and bound
licence-public-key fingerprint. Customer input and a request status alone must
never constitute approval. Use deny-by-default claim validation and short approval
validity. Require the established approval separation; payment alone is not an
approval and Stripe remains outside this work package.

Persist the approved canonical job hash, generated licence bytes and delivery
state in an access-controlled transactional ledger. The same job retries return
the same licence; a changed claim under the same ID is rejected. Use a durable
outbox and recover safely after signing but before delivery. Protect key unlock,
operator access, backups, revocation/rotation and auditing. Test with synthetic
keys first, then perform an owner-machine commissioning ceremony with the pinned
production public key. Never store key passphrases in scripts, arguments or logs.

Core local signer and idempotent SQLite ledger are now implemented and fixture-tested; see LOCAL-LICENCE-WORKER.md. Commissioning still requires authenticated approval/job transport, protected approval-key operation, delivery acknowledgements/outbox integration, Windows ACL validation, recovery and a witnessed production-key acceptance test. This plan does not activate unattended issuance.
