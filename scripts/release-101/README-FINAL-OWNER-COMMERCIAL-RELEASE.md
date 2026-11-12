# TEC EPR Clinic Edition 1.0.1 — Owner-controlled commercial release

**11 November 2026 · Fresh clinic installations only.** Existing-customer upgrade is **not supported** by this candidate and remains denied. The previously signed Clinic Edition 1.0.0 and all clinical installations stay untouched.

## Engineering progress already accepted

The exact unsigned candidate was independently downloaded and verified: 449 file digests, three scanned OCI image identities, 0 Critical/High according to the frozen scan attestation, Windows image compatibility and automatic image rollback, 26-table/clinical-upload hash parity, and authenticated VERIFIED lab HTTP/PDF on the isolated Windows synthetic recovery clone. The user has reported that ordinary staff logins and earlier clinical/site acceptance were approved; those previous sign-offs must be referenced against **this exact 1.0.1 frozen candidate** rather than automatically copied or backdated from the signed 1.0.0 release.

Frozen candidate manifest SHA-256: `66907861e79d59a463dbb3b0d178bfe5fba3dfb85c8c8347c152e0cbf8f58218`

Backend source commit: `91b848bfccb0951e010be8f566b4146a53b6a586`

Frontend source commit: `345384515c70dd7f6569e96f5c38b749b4ff986d`

The finalizer is pinned to the reviewed GitHub code that enforces `FRESH_INSTALLATIONS_ONLY` and marks existing-customer upgrades *not applicable*; it does **not** assert that a customer upgrade has passed.

## One-time owner workstation inputs

Use a standard user PowerShell session, Node.js 22+, Git for Windows with access to both private repositories, Python and OpenSSL, and AWS CLI with a **dedicated bucket-scoped private R2 publisher profile**. Signing and private object upload can occur only on the owner machine where the trusted RSA-4096 private key, the independent trusted public key and genuine approval references exist. Do not upload private keys, approval documents containing personal information, AWS credentials, signed download URLs, clinical records or passwords to ChatGPT, GitHub or the public website.

The signing program refuses to fabricate approvals. The approval template provided with this ZIP is deliberately **not approved**; enter the exact documented reviewer name, date and evidence reference for medical, security, offline recovery, publisher and gateway approvals. The existing-customer upgrade entry must stay `approved:false`, `notApplicable:true`, `scope:"FRESH_INSTALLATIONS_ONLY"`. Set the `assertion` to `APPROVED_FOR_COMMERCIAL_SIGNING` only after confirming all applicable evidence actually supports the frozen 1.0.1 release.

## Run on the owner's Windows machine

Extract this ZIP into a new folder, for example `C:\My_Applications\TEC-EPR-RC5-101-FINAL-RELEASE-TOOLS`. The existing verified candidate remains at `C:\Users\tlcok\TEC-EPR-RC5-101-Candidate-Review` and is **read-only**. First run `Check-TEC-EPR-101-Release.cmd`; it checks the previously verified candidate and writes a new approval template under `C:\Users\tlcok\TEC-EPR-1.0.1-FRESH-RELEASE-OWNER` without signing or uploading.

After reviewing the previously given approvals and securely locating the existing RSA publisher private key, run this **single final command** in PowerShell, substituting only actual existing owner-controlled local paths and the private AWS CLI profile name:

```powershell
$workspace = Join-Path $env:USERPROFILE 'TEC-EPR-1.0.1-FRESH-RELEASE-OWNER'
$template = Join-Path $workspace 'APPROVAL-TEMPLATE-FRESH-ONLY-NOT-APPROVED.json'
$approval = Join-Path $workspace 'APPROVED-TEC-EPR-1.0.1.json'
if (!(Test-Path -LiteralPath $approval)) { Copy-Item -LiteralPath $template -Destination $approval }
notepad.exe $approval
```

In Notepad, accurately record the already accepted **frozen 1.0.1 candidate** approval references, actual reviewer identities, UTC dates, and evidence paths; set the top-level assertion to `APPROVED_FOR_COMMERCIAL_SIGNING` only if supported. Each of the five applicable gates must have `approved:true`. Keep `existingCustomerUpgrade.approved:false`, `notApplicable:true`, `scope:"FRESH_INSTALLATIONS_ONLY"` (include a real reviewer/date/reason reference). Never invent the reviewer/date or borrow unrelated 1.0.0 sign-off references.

Identify the actual existing R2 CLI profile and the owner-controlled RSA4096 key paths **locally**:

```powershell
aws configure list-profiles
Test-Path 'C:\My_Applications\TEC-EPR-Publisher-Keys-1.0.0\private.pem'
Test-Path 'C:\My_Applications\TEC-EPR-Publisher-Trust\publisher-public-1.0.0.pem'
```

The private PEM path shown above was previously reported, **not independently verified**. If it is absent, locate the real protected key rather than generating/replacing the established publisher identity. The profile must be an actual configured, bucket-scoped R2 publisher profile; example names are **never executable arguments**.

Then from the extracted tools directory run, substituting only verified local file paths where needed:

```powershell
$r2Profile = Read-Host 'Enter the actual existing dedicated R2 publisher AWS CLI profile'
$privateKey = 'C:\My_Applications\TEC-EPR-Publisher-Keys-1.0.0\private.pem'
$publicKey = 'C:\My_Applications\TEC-EPR-Publisher-Trust\publisher-public-1.0.0.pem'
if (!(Test-Path -LiteralPath $approval -PathType Leaf) -or
    !(Test-Path -LiteralPath $privateKey -PathType Leaf) -or
    !(Test-Path -LiteralPath $publicKey -PathType Leaf)) { throw 'Required approved evidence or local signing key file missing' }
if ($r2Profile -notin @(aws configure list-profiles)) { throw 'Selected R2 AWS CLI profile not configured' }
.\Run-TEC-EPR-101-Commercial-Release.cmd --approval $approval --private-key $privateKey --public-key $publicKey --aws-profile $r2Profile
```

**Correction recorded 11 Nov 2026:** Old README examples contained literal placeholders such as `C:\<OWNER-PRIVATE-FOLDER>` and `<BUCKET-SCOPED-R2-PUBLISHER-PROFILE>`; executing those verbatim fails before signing, as expected. The canonical template path is printed by `Check-TEC-EPR-101-Release.cmd`. No new download of the utility bundle is required to follow these corrected instructions.

For an encrypted private PEM key, provide an existing local password file through the environment variable `TEC_PUBLISHER_KEY_PASSPHRASE_FILE`. Never paste the passphrase into the command line or chat.

The conductor clones **only new immutable tool checkouts** at verified commit SHAs, validates the actual unmodified candidate and CI scan, checks the real approval references, signs the 1.0.1 archive with the independently pinned existing RSA-4096 publisher identity, verifies the *entire* signed archive independently, then runs the TCL customer gateway's separate RSA and payload verifier. It uploads **only the distinct signed 1.0.1 archive** to the existing **private** Cloudflare R2 bucket under `tec-epr/clinic-edition/1.0.1/`, refuses overwrite, downloads an independent private readback and verifies SHA-256. It never modifies Docker, original patient/clinical data, a production website, or the previous 1.0.0 signed archive.

On complete success, the program writes `PRIVATE-GATEWAY-101-ACTIVATION-HANDOFF.json` in the owner-controlled release workspace. This contains nonsecret fixed signing/download evidence, the exact R2 key, hash, ETag and human evidence references; it **does not** enable downloads. Never send `GATEWAY_*` or `AWS_*` secrets to chat.

## Final website and production service cutover

The backend review branch is at `tlcoke2/tec_epr_backend` PR #83. The 1.0.1 private customer gateway is prepared in TCL PR #40, and the static software catalogue/download-login CTA is prepared in TCL PR #41. **These PRs are drafts.** The gateway intentionally refuses to start with release/download switches enabled unless the signed and independently read-back 1.0.1 evidence is configured. The old signed 1.0.0 is quarantined, never offered for download.

The production gateway requires a distinct production WorkOS OIDC/MFA tenant and dedicated commercial PostgreSQL (not staging), validated backup/restore, an HTTPS TCL customer subdomain and private R2 **read-only** credentials. Preserve customer two-person grant approval/revocation and short-lived signed GET links. Configure the exact nonsecret handoff fields and administrator approval references using the reviewed production change process, test production readiness and first-owner controlled signed download, then and only then set both `GATEWAY_RELEASE_APPROVED=true` and `GATEWAY_DOWNLOADS_ENABLED=true` in the approved production service.

On the static TCL site, only enable `VITE_TCL_CUSTOMER_DOWNLOAD_PORTAL_ENABLED=true` together with a reviewed exact `VITE_TCL_CUSTOMER_GATEWAY_ORIGIN=https://<APPROVED-CUSTOMER-HOST>.thuemancokelimited.com`. Before that moment, the page's customer download button remains **hidden**. Do not upload the archive to GitHub Pages or Railway ephemeral storage. End customers must verify the archive SHA-256 and publisher signature independently, then obtain a separately issued installation-bound license from TEC Healthcare. No anonymous download/auto-license/checkout is created.

## Stop conditions

Hold if any signed approval reference is missing or refers only to unrelated version 1.0.0, if the frozen source/scan digest changes, if a private-key fingerprint differs, if any member/signature/readback check fails, if R2 object already exists or HEAD is access-denied, if GitHub credentials cannot fetch exact pinned branches, or if production customer identity, MFA, database or hostname controls are not approved. Do not force-push, run `docker compose down -v`, mutate a patient database, or override release gates.

**Classification:** this kit prepares the last owner-controlled signing/private-storage operation. Until the owner workstation actually executes it and the production gateway is reviewed and enabled, 1.0.1 is **not signed, not published as downloadable customer software, and not generally released**.