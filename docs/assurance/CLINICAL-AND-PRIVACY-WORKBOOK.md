# Clinical safety and privacy workbook

Prepared 17 November 2026. Working evidence pack requiring the responsible owners' review. Blank or pending evidence is not approval. The released signed clinical archive is unchanged by this pack.

## Intended use — draft for clinical/regulatory review

TEC EPR Clinic Edition supports authorised trained healthcare staff with patient records and clinic/laboratory operations in a customer-controlled installation. Administrative records, appointments, billing and storage must be assessed separately from functions that interpret results, influence diagnosis or treatment, prescribe, calculate doses, operate instruments or use AI. This draft does not establish that all functions are outside medical-device regulation. Record the actual function, input, output, intended user, patient population, environment, clinical claim and excluded use for each released module before classification.

## Initial clinical hazard log

This is a starting hazard analysis, not an accepted safety case. A qualified clinical safety owner must assess likelihood, severity and residual risk, approve controls and link exact-version validation evidence.

| Hazard | Potential harm | Required control and evidence | Status |
| --- | --- | --- | --- |
| Wrong patient selected or duplicate record | Care given to wrong person | Patient identity checks, duplicate workflow and usability tests | Review required |
| Cross-facility disclosure or update | Confidentiality breach or incorrect care | Role/facility authorisation tests for every affected endpoint and attachment | Prior selected tests; full matrix required |
| Incomplete/incorrect prescription data | Medication error | Authorised prescriber workflow, validation, clinical review and audit | Clinical evidence required |
| Incorrect laboratory verification/cancellation | Wrong result used for care | Specimen/result lifecycle, concurrent-update tests and corrected-report trace | Prior selected tests; release trace required |
| PDF/report differs from saved record | Clinical decision based on incorrect output | Compare report/record, identifiers, units, reference ranges and verification state | Clinical evidence required |
| Stale edits overwrite current clinical data | Lost treatment information | Concurrency and conflict behaviour tests | Review required |
| Attachment linked to wrong patient | Disclosure or mistaken interpretation | Scoped access, association checks and hash verification | Review required |
| Licence expiry interrupts care | Delayed treatment or inaccessible workflow | Document expiry behaviour, advance warning, continuity/access-to-record policy and rehearsals | Safety decision required |
| System outage or corrupted backup | Missing records and delayed care | Encrypted backups, isolated restore tests, downtime procedures and RPO/RTO agreement | Per-site evidence required |
| AI output treated as medical authority | Inappropriate diagnosis or treatment | Defined intended use, evidence validation, visible limitations, human oversight and regulatory assessment | Do not assume approval |
| Unvalidated device/lab integration | Wrong result or patient association | Interface mapping, units, identifiers, error/quarantine and end-to-end validation | Per-interface evidence required |
| Excessive privileges or shared accounts | Unattributable or unauthorised actions | Named users, least privilege, staff exit process and access review | Per-site evidence required |

## Data-flow and privacy record

| Flow | Intended information | Boundary and action |
| --- | --- | --- |
| Website to WorkOS | Account identity and authentication | Verify supplier terms, transfers, retention and account recovery; passwords remain with the identity provider |
| Gateway to commercial DB | Account subject, organisation, country, request state and security records | Business information only; own-request export exists; document lawful basis and retention |
| Gateway to R2 | Private software object and short-lived signed delivery URL | No patient database or customer private key; restrict credentials and audit issuance |
| Customer EPR to its PostgreSQL/uploads | Patient and clinical records | Customer-controlled boundary; verify roles, host encryption, backup, retention, rights and clinical safety |
| Customer installation to TEC licence issuer | Installation identity and agreed licensing terms | No patient data or private signing key transfer; separate signing and verification identities |
| Remote support, AI or external integration | Depends on actual deployment | Inventory before enabling; establish contracts/BAA where relevant and validate transfers and minimisation |

For each deployment record the legal controller/processor, countries, categories and volume of data, Article 6 lawful basis, Article 9 condition where applicable, recipients/subprocessors, retention rationale, international-transfer mechanism, data-subject rights, safeguards, residual risk and approval date. Do not use marketing consent as a substitute for the lawful basis for clinical care.

## Incident and continuity runbook

1. Record discovery time, affected service, symptoms and incident owner. Keep patient data and secrets out of ordinary support tickets.
2. Preserve relevant logs and immutable evidence; restrict affected accounts or services using the established procedure. Do not wipe volumes or overwrite suspected evidence.
3. Assess exposure, integrity and availability with the privacy/security and clinical leads. Use established downtime care procedures when clinical functions are unsafe.
4. Determine notification obligations and deadlines with the responsible legal/privacy owner for the affected jurisdiction. Record the decision and communications; do not assume one deadline applies everywhere.
5. Recover from a validated separate restore, verify integrity/roles/clinical workflow, rotate exposed credentials and retest before reactivation.
6. Record root cause, corrective actions, owners, target dates and closure evidence; update the hazard log, risk assessment and training.

The site owner must specify RPO, RTO, on-call contacts, encrypted offsite backup location and drill frequency. Rehearse loss of a host, lost credentials, damaged uploads, licence recovery and unavailable external identity/payment services. Do not invent achieved recovery times.

## Release evidence required

Maintain a requirements-to-test register tied to the archive SHA-256 and all image IDs. Include identity/facility isolation, clinical workflows, failure modes, report accuracy, backup/restore, load/concurrency, accessibility/usability and support/upgrade/rollback procedures. Record test conditions, result, assessor and defects. A publisher signature proves artifact origin/integrity, not clinical correctness or regulatory compliance.

## Accountable roles needing appointment/confirmation

- Security/privacy owner: risk management, incident handling, access reviews and supplier contracts.
- Qualified clinical safety owner: intended use, hazards, clinical validation and safety case.
- Regulatory adviser: country/function applicability and conformity route.
- Commercial/tax owner: legal seller, registrations, approved contract and tax classification.
- Customer deployment owner: host security, staff training, backups and acceptance.

No individual is appointed or attested as having completed these duties merely by being named elsewhere in the project.
