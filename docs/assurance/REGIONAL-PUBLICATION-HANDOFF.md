# Regional publication handoff — 19 November 2026

The published licence-cd66121ca8df release remains the rollback and current customer release. This change does not alter Railway variables, R2 objects, customer grants, licences or signed archives. The new selector is opt-in: regional-a55a2b114a35. Both use release ID tec-epr-clinic-1.0.1, so existing access controls remain authoritative.

## Operator storage step

Use the existing authenticated Cloudflare dashboard on the owner's laptop. In private bucket `tec-epr-private-releases`, prefix `tec-epr/clinic-edition/1.0.1/`, upload these two existing files without renaming or overwriting any historical objects:

- `TEC-EPR-Clinic-Edition-1.0.1-Regional-a55a2b114a35.tar.gz`
- `TEC-EPR-Clinic-Edition-1.0.1-Regional-a55a2b114a35.tar.gz.publisher.sig`

They are in `C:\Users\tlcok\TEC-EPR-Regional-Release-20261119190317188-564b72`.

The verification script requires Node, AWS CLI with an existing R2 read profile and OpenSSL. No private signing key is needed. Never send credentials in chat. From a checkout containing this change:

```powershell
node .\scripts\verify-regional-r2.cjs `
  'C:\My_Applications\TEC-EPR-Publisher-Keys-1.0.1-ROTATED\public.pem' `
  "$env:USERPROFILE\Documents\TEC-EPR-Regional-R2-Readback.json"
```

It downloads both complete private objects, compares pinned hashes and size, checks RSA-4096 publisher SPKI and verifies the signature with Node and independently with OpenSSL. It reads the actual returned ETag. Existing output evidence is never overwritten. It does not upload or activate anything. If AWS CLI access is not configured, the infrastructure operator must supply an authenticated read route; a dashboard listing/ETag alone is insufficient verification.

## Activation after a passing readback

Deploy the tested selector code first with the old variables retained. Preserve an operator-side snapshot of current release-related Railway variables for rollback; do not paste secret-bearing exports in chat.

Set `GATEWAY_REGIONAL_R2_READBACK_JSON` to the actual generated JSON; set `GATEWAY_R2_101_EXPECTED_ETAG` to its ETag, `GATEWAY_R2_101_READBACK_SHA256` to its archiveSha256 and `GATEWAY_LICENCE_SIGNATURE_READBACK_SHA256` to its signatureSha256. Retain the existing download/approval flags and release ID. Bind the four existing approval reference variables to the recorded owner, medical, UAT and security evidence for this regional release. Existing authorisation is not requested again.

Select `GATEWAY_101_BUILD=regional-a55a2b114a35` only after all values are available. Verify service startup, anonymous download denial, authorised MFA-approved customer download, downloaded SHA-256 and detached signature, then installation/activation and Jamaica JMD versus US/Europe USD profile visibility. Preserve results; do not infer unperformed checks.

If the new selection fails, restore the complete previous release-variable snapshot, including `GATEWAY_101_BUILD=licence-cd66121ca8df` and its matching original ETag/readback. Restart and verify the retained working download. Switching only the build selector is insufficient because the archive hashes differ.

## Evidence boundaries

The regional archive SHA-256 is `0636d7a399f85e0cbd9a77175d11bf735df1f3b82f89825954c7575da8f26951`, size 266757194 bytes. Signature SHA-256 is `ebbe87da6dbde8898b1df16e8702615300a812cd5c4a013d9a72b9a99151872c`. Manifest is `a55a2b114a35fd3ad06233f9de7a2ea6f4b16de779adfbe1ca2975f0589bd762`.

Publisher verification evidence remains immutable. Its manualEvidenceClassification was Not supplied at signing. Supplementary `TEC-EPR-MANUAL-OWNER-ATTESTATION-0636d7a399f8.json` records the owner's later report of successful checks and lost original form. Do not rewrite it as independent observations or repeat signing. The 50-pass cash-corrected installed run and latest packaged CI are distinct evidence; exact latest-archive Windows installation identity has not been independently recorded.

Commercial closeout still distinguishes operating customer software/manual protected issuance from unattended licence delivery, external payment settlement, independent penetration assessment and site-specific regulatory certification. No automatic certification or live-payment activation is implied by publication.
