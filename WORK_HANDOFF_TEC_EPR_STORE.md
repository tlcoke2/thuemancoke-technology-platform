# Work handoff — TEC EPR enterprise store on TCL (29 Oct 2026)
## Authorised project objective
Use existing `www.thuemancokelimited.com` as TEC EPR product marketing, eligibility/trial enquiry, customer administration, **private** signed binary distribution and licence/renewal/support gateway. Keep the signed TEC EPR Clinic Edition v1.0.0 master untouched. Protect all patient DBs, Docker volumes, live CRM records and Railway/Cloudflare settings from unsafe modifications. Automate routine validated tasks, not irreversible approvals.

## GitHub state
- TCL application `tlcoke2/thuemancoke-technology-platform` — draft PR #30 from `feature/software-marketplace-and-epr-registration-20261029` to `main`.
- TEC backend `tlcoke2/tec_epr_backend` — security draft PR #5 and commercial draft PR #13; TEC frontend `tlcoke2/tec_epr_frontend` — draft security PR #2.
- TCL software store PR #30 adds `/software.html`, catalogue/registration API, consent-only lead capture and CRM handoff, fail-closed Turnstile, additive dedicated request table, frontend build plus backend synthetic tests.
- Review and reconcile CI, get independent code review, then stage on an isolated test environment before production merge.
- Detailed rollout policy: `SOFTWARE_MARKETPLACE_LAUNCH.md`; work items TCL #25–#29 and TEC backend #14–#19.

## Immutable owner asset / trust chain
Original signed archive retained ONLY on owner Windows host:
`C:\My_Applications\TEC-EPR-Commercial-Releases\TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz`
SHA-256 `E1C75BB867627CB60F0F5FF9737B602661550A15DF75F5DF52BF8C43835C8C0E`
Publisher SPKI SHA-256 `6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`.

**Never modify/rebuild/re-sign the master.** No plaintext private keys or patient data into cloud/chat/GitHub. Signer verification must use independently authenticated public key outside package; ensure same image digests and evidence. Prepare a distinct distribution **copy**.

## Work execution order
1. Audit exact TCL GitHub repo, current GitHub Pages deployment and Railway service settings read-only; document existing CRM, website/advertising/cookie/SMTP behaviours and production PostgreSQL backup/rollback. Confirm custom www vs apex behaviour before any DNS change.
2. Run PR #30 full tests and isolated PostgreSQL integration. Review risk: existing `CRM_ADMIN_KEY` shared browser key cannot be used for public customer auth; website CSP, CORS, Cloudflare WAF, CAPTCHA hostname/action and privacy retention require review.
3. Provision staging only (separate Railway environment/database and staging hostname), keep production intact. Validate form requests with synthetic organisations, consent records, email validation, CRM classification, negative tests and abuse/timeout recovery.
4. Establish independently controlled TEC/TCL publisher/distribution/legal relationship, approved price/tax schedule, Jamaican and UK privacy duties, refund, trial, EULA/SLA/DPA and medical/safety claims.
5. Private non-public Cloudflare R2 bucket for signed archives; retention and offsite immutable backup. Obtain only distinct verified distribution copy from owner's Windows environment through approved secure transfer; verify SHA-256, provenance, signature and software custody. Never host multi-GB packages on public GitHub Pages.
6. Implement separate commercial control-plane (PostgreSQL), OIDC/MFA, customer tenancy, authenticated grants and short-lived per-customer R2 pre-signed download URLs; audit download, support entitlement and installation identity.
7. Implement paid/pilot contract lifecycle, customer onboarding, licence request approval with two-person review, **offline separate RSA customer licence signing**, CRM lead conversion, renewal/expiry reminders and tested idempotent provider billing webhook. Live payments/trials only after account and price/legal approval.
8. Launch controlled Jamaican demo/pilot with synthetic patient records and security/UAT evidence; independently verify clinical release, operator signoff and recovery. International markets require additional country-specific checklists.
9. After formal release authorization, activate public product marketing and approved registration `SOFTWARE_LEADS_ENABLED=true` with Cloudflare Turnstile/WAF and staging-to-prod rollback. Do not enable anonymous installer download or instant signed entitlement generation.

## Hard prohibitions
No unapproved migration or production data deletion; no `docker compose down -v`, patient data ingestion to TCL, branch force-push, automatic GitHub security PR merging, published private bucket, leaked licence/private key, real customer charge or medical-device certification claims. Escalate unknown material requirements rather than guessing.
