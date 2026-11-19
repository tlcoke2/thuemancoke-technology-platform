# TEC EPR non-Stripe engineering closeout

Reviewed 18 November 2026. This register distinguishes completed implementation
from acceptance that needs responsible people, actual infrastructure or released
clinical UI evidence. No signed clinical archive, private key, approval, volume or
patient record is changed by this review.

## Completed in this review

- Added `/help` and a downloadable six-page PDF and plain-text customer guide inside the portal.
  The guide is tied to the published licence-enabled archive and verified source
  labels: Install.cmd, Subscription, Download licence request, Licence file,
  Verify and install. Help is linked from every gateway page and the account.
- Documented prerequisites, separate publisher/licence keys, initial sign-in,
  request/approval/licensing boundaries, renewal, synthetic acceptance and safe
  recovery. The portal does not accept installation JSON uploads or sign licences.
- Added explicit `--release 1.0.1-licence` support to the local byte-verification
  utility. Historical 1.0.0 verification keeps its previous default. This utility
  verifies bytes and SHA-256; it never claims detached-signature verification.
- Fixed hosted-checkout retry bodies to keep the integration label stable for a
  given order. Payment activation remains disabled and unchanged.
- Reconciled the readiness inventory with the deployed customer request review,
  payment options, billing ledger and current verification evidence.
- Added a fixed-target passive production checker. It does not sign in, create
  records, scan arbitrary hosts or change access. Record actual execution results
  separately. No pass is inferred merely because the script exists.

## Live edge compatibility correction

The live help HTML showed a support mail link rewritten to Cloudflare's email
protection route plus an injected email-decode script. The gateway intentionally
uses a script-free CSP, so that script could not run. Responses now include
`Cache-Control: no-store, no-transform` to prevent this documented edge rewrite,
while retaining the strict CSP. The passive check also verifies the support mail
link remains intact. This does not prove WAF/bot rule configuration.

Reference: https://developers.cloudflare.com/waf/tools/scrape-shield/email-address-obfuscation/

## Non-Stripe work that cannot honestly be called complete

| Item | Required closure evidence | Responsible party / boundary |
| --- | --- | --- |
| Full illustrated clinical user/admin manual | Exact released screens, role/module walkthroughs, recovery/error outcomes and clinical review | Clinical application owner and trained users; installation help is complete, full training is not |
| Clinical safety case | Named qualified safety owner, assessed hazards, controls, residual-risk acceptance and intended-use approval | Clinical safety owner |
| Medical-device applicability | Function/country assessment, especially decision support, AI, prescriptions and instrument interfaces | Qualified regulatory adviser |
| Privacy/HIPAA governance | Actual controller/processor roles, lawful bases, sensitive-data condition, DPIA, contracts/BAAs where applicable, retention and transfers | Legal/privacy owner and each deploying organisation |
| Independent penetration test | Agreed scope, independent report, remediation and retest | Independent security assessor; source tests are different evidence |
| Cloudflare WAF/bot/alerting | Actual account rule, mode, rate limits, origin protection and alert-delivery evidence | Authorised infrastructure operator; HTTP headers alone do not prove these settings |
| Customer host and disaster recovery | Device/backup encryption, off-host copy, isolated restore, measured RPO/RTO and downtime rehearsal | Each customer deployment owner |
| Automatic licence fulfilment | Protected signer, approved claims/modules/expiry, duplicate prevention, issuance ledger and key recovery/rotation | Separate signer boundary; current desktop/manual issuer remains operational |
| Legal commercial terms | Approved EULA, trial, support, refund and perpetual-scope terms | Owner/legal adviser; no approvals fabricated |

The existing workbook contains the initial hazard log, data flows and incident
runbook. It is a working evidence pack, not completed regulatory approval.

## Routine operating procedure

1. Customers use `/start` and their verified accounts. Private requests are listed
   under `/customer/requests`. Payment-link requests do not issue links or licences.
2. Appointed operators complete recent MFA via `/account`, review
   `/admin/software-requests` and update request status using the protected form.
   Stale/terminal updates are rejected and recorded transactionally.
3. Separate existing two-person approvals govern download grants. A request status
   or payment cannot replace the independent approval.
4. After approved download, customers use `/help`, install to a new folder and
   obtain the installation JSON from Subscription. The portal request form records
   an enquiry; the JSON is sent via the agreed support channel, without patient data.
5. Use the protected owner-side issuer for the agreed organisation, Installation
   ID, modules and expiry. Return a signed .teclicense through the agreed channel.
   Never copy the private signing key into Railway, the portal or a customer package.
6. For an incident preserve evidence, restrict the affected workflow and involve
   privacy/security/clinical owners. Never reset production volumes as a repair.
7. Run `python scripts/check-production-gateway.py --evidence NEW-FILE.json` for
   passive gateway checks. It requires curl and checks only fixed authorised URLs.
   An unavailable endpoint produces failure, not an assumed pass.
8. Before any clinical rollout, close the site-specific acceptance items above.
   Preserve the original signed release and separate evidence for every change.

## Further implementation under existing owner approval

- Added the source-verified [clinical module manual](TEC-EPR-CLINICAL-MODULE-MANUAL.md). Installed-screen illustrations, outstanding workflow acceptance and clinical review remain explicit.
- Reconciled historical approval evidence with the exact final release in [the approval crosswalk](assurance/FINAL-RELEASE-APPROVAL-CROSSWALK.md). Existing authorisation is retained; no general approval is being requested again.
- Added a release-bound local evidence checker with negative tests and a read-only Cloudflare collector. Neither treats missing evidence as a pass.
- Prepared concrete independent-assessment, privacy/regulatory, isolated-recovery and protected-signer work packages in [the execution plan](assurance/ASSESSMENT-AND-RECOVERY-PLAN.md). These are execution preparation, not fabricated completed assessments.

- Implemented a separate [local licence worker](assurance/LOCAL-LICENCE-WORKER.md): pinned approval signature, encrypted signing key, claim validation, durable duplicate prevention and retry-safe local output. Production commissioning, authenticated approval transport and delivery remain outstanding. No production private key was accessed.

## Owner clarification and regional/desktop implementation

The owner reports that clinical, legal and privacy work was completed in-house,
and Cloudflare authentication/protected access was completed through the owner's
Edge browser. These are retained as owner-reported evidence; cloud-browser sign-in
is not being requested again. See [the owner update](assurance/OWNER-CLOSEOUT-UPDATE-20261118.md).
Both JMD and USD are required. The new regional candidate retains them separately
and binds the installation to a consistent currency. The protected desktop issuer
now has a portable GUI package with local ACL/key preflight and duplicate-safe
issuance. Actual Windows commissioning is the next owner-assisted step.
