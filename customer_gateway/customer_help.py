"""Version-specific customer guidance. No credentials or clinical records are served."""
from pathlib import Path
from fastapi.responses import HTMLResponse, Response
try:
    from .ui import page
except ImportError:
    from ui import page

ARCHIVE = 'TEC-EPR-Clinic-Edition-1.0.1-Licence-cd66121ca8df.tar.gz'
SHA256 = 'c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059'
LICENCE_SPKI = 'feba748a1b088c114f0e63e49d28b6203ca7d28c0b72e75aace3511379342f26'
PUBLISHER_SPKI = 'b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a'

GUIDE = f'''# TEC EPR Clinic Edition 1.0.1 — Customer installation and activation

Scope: the signed, licence-enabled fresh Windows installation. This is not an
upgrade procedure, full clinical training manual or regulatory certificate.

1. Register at https://customers.thuemancokelimited.com/start, verify your email
   and sign in. Use My software requests for demo, subscription, outright purchase
   or installation licensing. Requests, payments and approvals are separate.
2. After access approval, obtain the release archive and detached publisher
   signature from Customer access. Archive: {ARCHIVE}
   Expected archive SHA-256: {SHA256}
   Expected size: 289009684 bytes. Verify the SHA-256 and publisher signature before
   extraction, using an independently authenticated publisher public key.
   Publisher SPKI SHA-256: {PUBLISHER_SPKI}
   A matching checksum alone does not authenticate the publisher. If you cannot
   verify the signature, contact support before installation. Keep signed links private.
3. Prepare the validated Windows 11 computer with Node.js 22 or newer and Docker
   Desktop running Linux containers with Compose. Obtain prerequisites from their
   official vendors. The offline images do not install these prerequisites.
   Confirm site-specific disk, memory, device encryption and backup requirements.
4. Extract into a NEW folder. Double-click Install.cmd. Enter organisation,
   country, timezone, facility, administrator and local port details when asked.
   Keep the folder and the local URL printed by the installer. This is not a
   repair or upgrade command for an existing installation.
5. The approved package includes tec-licence-verification.pem. It creates the
   local public.pem verification material itself. Do not supply a private key or
   borrow a public key from another build. Unexpected key prompts mean you must
   stop and confirm the package identity. Licence SPKI SHA-256: {LICENCE_SPKI}
6. Sign in at the installer's local URL using your administrator email and the
   initial password in bootstrap-password.txt. Protect that temporary password;
   confirm access before removing the temporary file according to local policy.
7. Open Subscription. Under Install or renew a subscription choose Download
   licence request. Keep tec-epr-licence-request.json; it contains only the
   request format and Installation ID. Submit an Installation licence request
   in the customer portal. The web form currently records the request; it does
   not upload this JSON or issue a licence automatically. Supply the request
   file through your agreed support channel to tlcoke@hotmail.com.
8. TEC confirms organisation, modules and expiry separately and returns a signed
   .teclicense file. In Subscription, choose that file under Licence file, then
   select Verify and install. Confirm Customer installation, Installation ID,
   customer name, expiry and module entitlements. Do not alter the licence file.
9. Before clinical use, test with synthetic records: named administrator login,
   clinician creation, patient assigned to that clinician, appointment creation
   and read-back. Check purchased modules, reports, roles, facility isolation,
   attachments, audit and recovery. A licence is not clinical safety acceptance.
10. Assign named least-privilege staff accounts. Secure the Windows host and
    backups. Follow the package's backup/restore instructions and rehearse an
    encrypted off-host restore into a separate empty environment. Preserve the
    installation identity, configuration, database and uploads together.

## Requests, downloads and account help

My software requests shows your own requests and status. Received means recorded;
reviewing means an operator is assessing it; awaiting customer means follow-up is
needed; closed/rejected do not grant access. Contact support with the request ID.
Use Export my request data for your commercial request history. It is not a
patient-record export or complete identity-provider data-access response.

Payment-link requests can be submitted per plan at /payments. A request is not a
payment link or confirmed payment. Stripe activation is separate. Outright purchase
and larger Enterprise deployments are private quotations.

Session expired: choose Sign in securely and start a fresh sign-in. Keep your
identity-provider recovery methods secure. Appointed operators use /account for
additional authenticator verification and /admin/software-requests for the inbox.
Do not share named administrator accounts or disable MFA to work around access.

## Problems and safe recovery

- No download: check customer approval, grant validity and recent sign-in.
- Licence rejected: check the original Installation ID, organisation, expiry,
  approved modules and the bundled verification identity. Preserve the request.
- Expiry approaching: request renewal before expiry; do not assume a grace period
  or continued clinical access. Rehearse the site's continuity procedure.
- Installer error: preserve the folder and error text, then contact support.
- Clinical issue: stop the affected workflow and use the organisation's clinical
  escalation/downtime procedure. Do not use synthetic acceptance as full validation.
- Do not delete Docker volumes, reset a database, regenerate installation IDs or
  run docker compose down -v to repair a live installation.
- Do not expose the database port. LAN/cloud deployment needs managed HTTPS,
  correct origins and a reviewed firewall and support arrangement.

Support: tlcoke@hotmail.com. Send request/installation IDs and non-sensitive error
text. Do not send patient records, passwords, private keys or card security codes.

The gateway changes do not modify the signed clinical archive. Full illustrated
module training, independent penetration testing, deployment-specific privacy,
clinical safety and regulatory approval remain separate acceptance requirements.
'''


def register(app):
    @app.get('/help', response_class=HTMLResponse)
    def help_page():
        return page('Install, activate and get support',
            '<section class="card panel-gradient"><h2>Your customer guide</h2><p>For the signed TEC EPR Clinic Edition 1.0.1 fresh Windows installation. Keep a copy with your installation records.</p><a class="button" href="/help/customer-guide.pdf">Download PDF installation guide</a> <a class="button secondary" href="/help/customer-guide.txt">Plain-text guide</a></section>'
            '<div class="grid"><section class="card"><h2>1. Register and download</h2><p>Create your account, verify your email and request the software you need. Once approved, download the archive and its publisher signature from Customer access.</p><a href="/start">Register / sign in</a> · <a href="/customer/requests">My software requests</a> · <a href="/customer">Approved downloads</a></section>'
            '<section class="card"><h2>2. Verify and install</h2><p>Check the archive checksum and independently verify the publisher signature. Prepare Windows 11, Node.js 22+ and Docker Desktop with Linux containers. Extract to a new folder and double-click <strong>Install.cmd</strong>. Follow its wizard and keep the displayed local URL.</p><p>The licence verification public key is included. Customers never need TEC’s private key.</p></section>'
            '<section class="card"><h2>3. Request your licence</h2><p>Sign in locally using your setup administrator and initial password. Open <strong>Subscription</strong> and choose <strong>Download licence request</strong>. Submit an Installation licence request in the portal, then supply the JSON through your agreed support channel.</p><p>The current portal records requests; it does not upload the installation JSON or generate licences automatically.</p><a href="/customer/requests?intent=licence">Request an installation licence</a></section>'
            '<section class="card"><h2>4. Apply and validate</h2><p>When TEC returns your signed <strong>.teclicense</strong>, select it under <strong>Licence file</strong> in Subscription and choose <strong>Verify and install</strong>. Check customer, Installation ID, expiry and modules. Use synthetic data for validation before clinical approval.</p></section></div>'
            '<section class="card"><h2>Verify the exact release</h2><p>Archive: <code>' + ARCHIVE + '</code></p><p>Size: 289009684 bytes. Expected SHA-256:</p><code class="code">' + SHA256 + '</code><p>A checksum verifies bytes; it does not replace independent publisher-signature verification. The publisher identity and licence identity are different. Full fingerprints are in the downloadable guide.</p></section>'
            '<section class="card"><h2>Support, renewal and recovery</h2><p>Contact <a href="mailto:tlcoke@hotmail.com">tlcoke@hotmail.com</a> with your request ID, Installation ID and non-sensitive error text. Request renewal before expiry and maintain a tested downtime/backup plan. Never delete volumes or reset clinical data as a repair.</p><p>Do not send patient records, passwords, private signing keys or payment-card details.</p><a href="/customer/requests">Track requests</a> · <a href="/payments">Payment options</a> · <a href="/account">Account and authenticator</a></section>',
            eyebrow='TEC EPR CUSTOMER HELP', intro='A clear path from approved download to your own licensed installation.')

    @app.get('/help/customer-guide.txt')
    def customer_guide():
        return Response(GUIDE, media_type='text/plain; charset=utf-8', headers={
            'Content-Disposition':'attachment; filename="TEC-EPR-1.0.1-Customer-Guide.txt"'})

    @app.get('/help/customer-guide.pdf')
    def customer_pdf():
        return Response(Path(__file__).with_name('TEC-EPR-1.0.1-Customer-Guide.pdf').read_bytes(),
            media_type='application/pdf', headers={
                'Content-Disposition':'attachment; filename="TEC-EPR-1.0.1-Customer-Guide.pdf"'})
