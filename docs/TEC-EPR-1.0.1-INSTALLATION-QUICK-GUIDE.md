# TEC EPR 1.0.1 — customer installation and activation
Version 1 · 17 November 2026
Scope: fresh Windows customer installation of the signed licence-enabled release. This is a quick guide; it is not an upgrade procedure or complete clinical training manual.

## 1. Register and request access
Open https://thuemancokelimited.com/software.html and select Customer centre. Create your account, verify your email and keep your sign-in credentials private. In My software requests select demo, subscription, outright quotation or installation licence. Submit organisation and country only. Do not upload patient data or private keys.

## 2. Download the approved release
Once access has been approved, open My approved downloads. Obtain the archive and detached publisher signature through the private links. The archive is TEC-EPR-Clinic-Edition-1.0.1-Licence-cd66121ca8df.tar.gz.
Expected SHA-256:
c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059

Verify the archive and publisher signature using the approved verification instructions and an independently authenticated publisher public key. A matching checksum alone does not authenticate a publisher. If verification fails, stop and contact support.

## 3. Prepare the computer
Use the validated Windows 11 environment, Node.js 22 or newer and Docker Desktop with Linux containers and Compose available. Start Docker before installation. Obtain prerequisites from their official vendors. The offline application image bundle does not itself install Docker or Node. Confirm adequate disk/RAM against your deployment sizing assessment; hardware sizing has not been universally certified.

Extract into a new dedicated folder. Retain the entire installed folder for operation and recovery. Do not install over an existing live system or redistribute an installed folder containing secrets.

## 4. Run the installer
Double-click Install.cmd in the extracted package. Enter the organisation, facility and administrator details requested by the wizard. Keep the displayed local port/URL. The licence-enabled package carries tec-licence-verification.pem and validates it against the manifest; the customer does not need the owner's private key or a public-key folder copied from an unrelated build. If asked unexpectedly for an external verification key, stop and confirm that the exact approved licence-enabled package was downloaded.

The wizard creates local configuration, a unique installation identity, isolated containers and an initial administrator. It must not reset an existing clinical database. Follow its reported errors; never use volume deletion or schema reset as a repair.

## 5. Sign in and activate
Open the local URL printed by the installer. Sign in using the administrator email entered during setup and the initial password in bootstrap-password.txt. Store that password securely; remove the temporary password file after confirming access.

Open Subscription and obtain the installation licence request/Installation ID. Send the request through the agreed support process; the current web request form records the request but does not upload the installation JSON. TEC issues a signed .teclicense file for the agreed organisation, installation, modules and expiry. Apply it in the application's licensing/Subscription screen, then confirm customer name, installation ID, expiry and authorised modules.

The licence verification public-key SPKI SHA-256 is:
feba748a1b088c114f0e63e49d28b6203ca7d28c0b72e75aace3511379342f26
This is separate from the publisher signing identity.

## 6. Validate before clinical use
Use synthetic data to check administrator login, staff roles/facility scope, doctor creation, patient registration with assigned doctor, appointment creation and read-back. Verify the clinical modules purchased, reports, audit records, attachments and recovery. A successful install or licence activation is not clinical acceptance of every feature.

Demo work uses synthetic records. Real patient use requires the customer's privacy, security and clinical-safety approval and the applicable regulatory assessment.

## 7. Operate and recover
The default installation is local. Staff LAN/cloud access requires a managed HTTPS reverse proxy, exact origin configuration and a reviewed firewall; do not publish the PostgreSQL port. Assign named staff accounts and least-privilege roles. Protect the host with supported updates, device encryption, endpoint protection and secured backups.

Back up database, uploads, installation identity and configuration using the package's documented backup procedure. Keep encrypted off-host copies and rehearse restoration into a separate empty environment. Never run docker compose down -v against a live installation. Do not regenerate installation IDs to repair a licence.

## 8. Support and common problems
- Session expired: start a fresh sign-in; never disable authentication.
- No download entitlement: review the account/request status; registration is not a download grant.
- Licence rejected: check installation ID, organisation, expiry and that the correct licence verification identity is bundled. Do not replace the public key with an arbitrary key.
- Installer failure: retain the folder and error text, protect secrets and contact support. Do not delete volumes.
- Clinical workflow issue: stop the affected workflow and follow the organisation's clinical escalation procedure.

Support: tlcoke@hotmail.com. Never email patient records, passwords or signing private keys.

## Full manual scope still to finalise
The final illustrated user/admin manual must be checked against the released UI for patients, users, facilities, appointments, billing, discharges, laboratory/specimens, medicines/prescriptions, pricing/codes, quality control, tasks/treatments, uploads, LIMS/integrations, settings, exports, instruments and optional AI. Each chapter needs role prerequisites, steps, expected results, error recovery, audit behaviour and safety limitations.
