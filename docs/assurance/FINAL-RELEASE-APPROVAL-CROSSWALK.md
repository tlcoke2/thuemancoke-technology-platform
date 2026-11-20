# Approval evidence reconciliation

Owner authorisation to continue implementation is already given. No new general
permission to proceed is requested by this reconciliation.

| Evidence | Established scope | Treatment |
| --- | --- | --- |
| APPROVED-TEC-EPR-1.0.1.json | Earlier manifest beginning 66907861; earlier backend/frontend revisions; medical-director, security, DR, publisher and gateway references; also contains a template-only note | Preserve original. Retrieve underlying documents and determine applicable unchanged functions; do not convert a template reference into a new signature |
| FINAL-LICENCE-ARCHIVE-VERIFIED.json | Final manifest cd66121ca8dfdbec30899be998cfb30d8ee13570e93cab967effcb9d83c3bf1b; final archive c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059; signature and packaged checksums verified | Integrity evidence for the final distribution, not a clinical/legal opinion |
| Owner-reported installation and licence application | Installation 038eb67d-7845-483c-bb84-21b5058bc22e; customer HCCM; stated expiry 31 December 2026 | Acceptance evidence for that installed licence workflow; not unattended signer deployment |
| Owner-reported synthetic workflow | Run 19ad78abfc92; anonymous denial, administrator login, facility/licence, doctor, patient and appointment readback | Reuse as reported functional evidence; do not label independently witnessed |
| Gateway CI and passive verification | 279 tests and deployed endpoint/PDF checks recorded in existing repository evidence | Application engineering evidence; not an independent penetration report or account-side Cloudflare configuration audit |

## Release-bound decision format

Use `scripts/assurance/verify-closeout.py` with a private evidence directory.
The template `closeout-evidence.template.json` deliberately has no accepted
signoffs. Populate it from actual responsible-owner decisions and hash the
supporting local files. Do not commit medical records, private contracts, keys or
sensitive assessor reports to this public repository. Preserve originals privately.

The checker rejects another release, duplicate controls, template decisions,
missing evidence, altered hashes and an unasserted independent test. It checks
completeness only: it cannot authenticate a person's identity, expertise or report
conclusions. A successful check does not enable deployment or create certification.
An earlier approval can be used when its actual scope covers the final release;
otherwise record the delta review needed, not a fictitious full reapproval.
