# TEC EPR Clinic Edition 1.0.0 — private R2 distribution
**Status:** Secure operations guide. The source-signed release master is preserved. Upload is an operator action on a trusted Windows system, never an automatic GitHub CI task.

## Why R2 Standard
Cloudflare R2 Standard offers **10 GB-month storage, one million Class A operations and ten million Class B operations per month** in its free tier; subsequent standard storage is currently US$0.015/GB-month with no R2 internet egress fees (official R2 pricing, 29 October 2026). Plans/fees may change. Railway and GitHub Pages continue serving software marketing/CRM only. Keep protected binary archives outside Pages/static public assets.

## Authorisation and prerequisites
1. Confirm TEC Healthcare/TCL signed authority to distribute and support the software; verify applicable terms, customer export rights and support obligations.
2. On the owner Windows machine, retain **unchanged**:
   - `C:\My_Applications\TEC-EPR-Commercial-Releases\TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz`.
   - SHA-256: `E1C75BB867627CB60F0F5FF9737B602661550A15DF75F5DF52BF8C43835C8C0E`.
   - Trusted publisher public key from **independent authenticated custody**; SPKI SHA-256: `6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733`.
3. Ensure **separately extracted** signed release directory exists. Use the current backend security checkout's `scripts/verify-signed-market-release.cjs` as `-VerifierScript`. Never extract/operate inside original master.
4. Create a **private** Cloudflare R2 bucket, with public `r2.dev` and public custom domains disabled. Configure R2 S3 credentials scoped to **that bucket only**, held in Windows secure credential storage or ephemeral AWS CLI profile, never GitHub or TCL backend. Enable budget/usage alerts, version/retention controls and independent encrypted backup of the source archive.
5. Prepare Node.js 22+, AWS CLI and a validated R2 profile on publisher workstation. Credentials should not be echoed or saved in plain text command history.

## Dry run (first, no cloud upload)
```powershell
.\scripts\Publish-TEC-EPR-Private-R2.ps1 `
  -VerifiedReleaseDirectory 'C:\My_Applications\TEC-EPR-Commercial-Releases\VERIFIED-SIGNED-1.0.0' `
  -TrustedPublisherPublicKey 'C:\My_Applications\TEC-EPR-Publisher-Trust\publisher-public-1.0.0.pem' `
  -VerifierScript 'C:\My_Applications\TEC-EPR-security-build\scripts\verify-signed-market-release.cjs'
```
Replace **example** paths with your real existing extracted release and separately authenticated public key. This checks archive SHA-256, publisher fingerprint and detached signed manifest integrity. It makes no changes to your signed archive or any customer installation.

## Approved private upload (distinct archive copy only)
```powershell
.\scripts\Publish-TEC-EPR-Private-R2.ps1 `
  -VerifiedReleaseDirectory '<EXISTING VERIFIED RELEASE DIRECTORY>' `
  -TrustedPublisherPublicKey '<INDEPENDENT PUBLIC PEM>' `
  -VerifierScript '<CURRENT RELEASE VERIFY JS>' `
  -R2AccountId '<CLOUDFLARE R2 ACCOUNT ID>' `
  -R2Bucket '<PRIVATE BUCKET NAME>' `
  -PrivateBucketConfirmed `
  -Upload
```
The script refuses SHA/key mismatch, missing independently verified signed release, missing prerequisites or attempted overwrite. It checks remote size and SHA metadata after upload. **For customer release**, download a separate private test copy and independently verify SHA and signature again before granting access; metadata alone is not cryptographic read-back proof.

## Access control remains a separate P0 gate
No public download URL is generated. Before opening sales, implement an OIDC/MFA customer portal and approval registry, restricted short-lived customer-specific presigned GET URLs (expiry 5–15 minutes), release verification guide, audit logs, rate limiting, entitlement checks and re-download/revocation policy. Do not derive a download entitlement solely from a Stripe webhook. Do not place publisher/entitlement signing private keys in R2, Railway, GitHub or browser.
