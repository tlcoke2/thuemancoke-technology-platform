# TEC EPR regulatory readiness — evidence gaps
Review date: 17 November 2026
Status: scoped readiness review, not a compliance certificate or worldwide market authorisation.

## Conclusion
The signed release and successful installation tests demonstrate particular technical outcomes. They do not establish universal HIPAA/GDPR compliance or medical-device approval. No independent compliance audit, complete clinical safety case, regulator clearance, certified quality system or full contract/subprocessor assessment has been verified in this review. Do not publish certification badges or claim that every regulatory check will pass.

## Evidence available
The project has a pinned signed archive, a separate licence verification identity, reported Windows installation/activation acceptance, synthetic doctor/patient/appointment creation evidence, private distribution with tenant/grant controls, and administrator MFA. The recent gateway tests cover selected access-control and request validation behaviours. This is useful evidence, not a complete clinical or compliance test programme.

## Market matrix
| Area | What must be established | Current conclusion / required evidence |
| --- | --- | --- |
| US HIPAA | Applicability, covered entity/business associate responsibilities, documented risk analysis, administrative/physical/technical safeguards, access/audit/integrity/transmission controls, contingency and incident procedures, BAAs when applicable | Not verified compliant. Inventory every ePHI flow, supplier and support path. Customer-controlled installation does not remove contractual duties when TEC accesses ePHI. |
| UK GDPR / Data Protection Act | Article 6 lawful basis plus Article 9 health-data condition; controller/processor roles; DPA; transparency; retention; rights; security; DPIA where required; transfer safeguards | Not verified compliant. Produce a deployment-specific data map, DPIA and processing records; verify backup/export/erasure restrictions and breach handling. |
| EU GDPR | Equivalent deployment-specific controller/processor, special-category, rights, transfer and security analysis under EU law | Not verified. UK documentation alone is not evidence that EU representative or transfer obligations are satisfied. |
| Jamaica | Data Protection Act and OIC standards, sensitive health-data duties, DPO/registration applicability, retention, security and overseas transfers | Assess HCMC and each customer separately with their responsible privacy officer. |
| UK medical devices | Intended purpose and function-by-function qualification/classification; applicable conformity and MHRA registration route where software is a device | No device approval verified. Patient administration/records differ from diagnostic, treatment, AI and laboratory interpretation functions. |
| EU MDR / IVDR | Qualification/classification under intended purpose, including decision support and IVD functions; technical documentation and conformity assessment where applicable | No CE/device conformity evidence verified. Use current MDCG guidance for a formal assessment. |
| US FDA | Function-by-function device/CDS assessment using current guidance; applicable submission/quality/cybersecurity duties | No FDA clearance verified. Do not imply that a general EPR is FDA approved. |
| NHS England | DCB0129 manufacturer clinical risk management and DCB0160 deployment applicability; clinical safety officer, hazard log, safety case; procurement/DSPT/DTAC as relevant | Not established by a Medical Director signoff alone. Prepare the required clinical risk documentation and assessment. |
| Engineering standards | Applicability and evidence for ISO 14971 risk management, IEC 62304 software lifecycle, IEC 62366-1 usability, ISO 13485 quality systems, ISO/IEC 27001 and relevant interoperability standards | Requirements mapping needed. No certification or standard conformance is asserted. |

## Priority work
1. Publish and approve a precise intended-use statement and excluded uses for every module; assess AI, prescribing, laboratory interpretation and device integration separately.
2. Build a requirements-to-test matrix for the exact released image IDs. Preserve clinical validation, access isolation, audit completeness, backup/restore, concurrency, usability and failure-mode evidence.
3. Appoint regulatory, clinical-safety and privacy owners. Maintain a hazard log, risk controls, residual-risk decisions and post-market incident process.
4. Create HIPAA security risk analysis/BAA applicability records and UK/EU/Jamaica processing/DPIA/transfer records.
5. Verify storage encryption, privileged support access, device/host hardening, retention, recovery, audit tamper resistance and incident response in each deployment.
6. Obtain an independent security assessment and qualified jurisdiction-specific regulatory review before making compliance or clearance claims.
7. Finalise customer-facing installation and module guides against the actual release and role permissions; assess accessibility and training outcomes.

## Official sources checked
- HHS Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/index.html
- HHS certification FAQ: https://www.hhs.gov/hipaa/for-professionals/faq/are-we-required-to-certify-our-organizations-compliance-with-the-standards/index.html
- ICO special-category rules: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-are-the-rules-on-special-category-data/
- MHRA software guidance: https://www.gov.uk/government/publications/medical-devices-software-applications-apps
- FDA Clinical Decision Support Software (January 2026): https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
- EU MDCG 2019-11 rev.1 (June 2025): https://health.ec.europa.eu/system/files/2025-06/mdcg_2019_11_en.pdf
- NHS clinical safety: https://digital.nhs.uk/services/clinical-safety/clinical-risk-management-standards
- Jamaica OIC data protection standards: https://www.oic.gov.jm/page/data-protection-standards

HHS's current Security Rule page still identifies the January 2025 cybersecurity amendment as a proposed rule; a proposal is not treated as an effective final requirement here. This is a bounded review of the sources above, not an exhaustive survey of every country.
