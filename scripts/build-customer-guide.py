from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from pathlib import Path
from xml.sax.saxutils import escape
import fitz

import sys
regional = '--regional' in sys.argv
out=Path('customer_gateway/TEC-EPR-1.0.1-Regional-Customer-Guide.pdf' if regional else 'customer_gateway/TEC-EPR-1.0.1-Customer-Guide.pdf')
Path('tmp/pdfs').mkdir(parents=True,exist_ok=True)
navy=colors.HexColor('#0b1834');teal=colors.HexColor('#087f82');muted=colors.HexColor('#526478')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleTEC',fontName='Helvetica-Bold',fontSize=30,leading=35,textColor=navy,spaceAfter=20))
styles.add(ParagraphStyle(name='SubTEC',fontSize=13,leading=20,textColor=muted,spaceAfter=16))
styles.add(ParagraphStyle(name='BodyTEC',fontSize=10.5,leading=16,textColor=navy,spaceAfter=11))
styles.add(ParagraphStyle(name='HeadingTEC',fontName='Helvetica-Bold',fontSize=16,leading=21,textColor=teal,spaceBefore=14,spaceAfter=12))
styles.add(ParagraphStyle(name='StepTEC',fontName='Helvetica-Bold',fontSize=11,leading=16,textColor=navy,spaceBefore=10,spaceAfter=6))
styles.add(ParagraphStyle(name='CodeTEC',fontName='Courier',fontSize=8,leading=12,textColor=navy,spaceAfter=12))
story=[]
def para(s,style='BodyTEC'):story.append(Paragraph(s,styles[style]))
def step(title,text):story.append(KeepTogether([Paragraph(title,styles['StepTEC']),Paragraph(text,styles['BodyTEC'])]))
def section(n,title):
 if story:story.append(PageBreak())
 para('TEC EPR CLINIC EDITION 1.0.1','SubTEC');para(f'{n:02d}  {title}','TitleTEC')
def footer(c,doc):
 w,h=A4;c.setFillColor(navy);c.rect(0,h-15,w,15,fill=1,stroke=0)
 c.setStrokeColor(colors.HexColor('#dae2ec'));c.line(48,45,w-48,45)
 c.setFont('Helvetica',8);c.setFillColor(muted);c.drawString(48,30,'Thueman Coke Limited | Customer installation and activation | Version 1.0.1')
 c.drawRightString(w-48,30,str(doc.page))
section(1,'Your installation guide')
para('From approved download to a licensed customer installation.','SubTEC')
para('Prepared 19 November 2026. For the signed, licence-enabled fresh Windows installation. Keep this guide with your installation records.')
para('Start here','HeadingTEC')
para('<link href="https://customers.thuemancokelimited.com/help" color="#087f82">customers.thuemancokelimited.com/help</link><br/>Customer account: customers.thuemancokelimited.com/start<br/>Support: tlcoke@hotmail.com')
step('Your four stages','Register and request access; verify and install; request and apply your installation licence; validate and prepare safe operation.')
step('Important scope','This is an installation, activation and support guide. It is not an upgrade procedure, a complete clinical module training manual, a medical-device approval or a HIPAA/GDPR certificate. Clinical use needs the deploying organisation\'s acceptance.')
step('What customers need','A validated Windows 11 computer, Node.js 22 or newer, Docker Desktop running Linux containers with Compose, the approved signed archive and named administrator details. The offline image bundle does not install Docker or Node.')
step('What customers never need','TEC\'s private publisher or licence signing keys. The correct licence verification public key is included in the approved package.')
section(2,'Register, verify and install')
step('1. Create your verified account','Open the customer account page, register, verify your email and sign in. In My software requests select demo, subscription, outright quotation or installation licence. Use business details only.')
step('2. Obtain your approved software','Customer access lists approved private downloads. Download the archive and detached publisher signature. Keep delivery links private; approval and link expiry are separate from licence activation.')
step('3. Verify before extraction','Compare the archive SHA-256 and size below. Independently authenticate the publisher public key and verify the detached signature. A matching checksum alone does not authenticate the publisher. Contact support if signature verification is unavailable or fails.')
para('Approved archive','HeadingTEC')
archive_block='TEC-EPR-Clinic-Edition-1.0.1-Licence-cd66121ca8df.tar.gz\nSize: 289009684 bytes\nSHA-256:\nc4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059'
if regional:
 archive_block=archive_block.replace('Licence-cd66121ca8df','Regional-a55a2b114a35').replace('289009684','266757194').replace('c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059','0636d7a399f85e0cbd9a77175d11bf735df1f3b82f89825954c7575da8f26951')
story.append(Preformatted(archive_block,styles['CodeTEC']))
if regional: step('Regional pricing','Jamaica uses JMD; US and UK/Europe use USD with separate approved pricing schedules. Confirm the country and currency during setup. This is not an exchange-rate conversion.')
step('4. Use a new installation folder','Start Docker. Extract into a NEW folder and double-click Install.cmd. Enter organisation, country, timezone, facility, administrator and local port details when asked. Keep the printed local URL and retain the installation folder. Do not install over a live system.')
step('Unexpected key prompt or installer error','Stop and confirm you downloaded this exact licence-enabled package. It includes tec-licence-verification.pem and creates the local public.pem itself. Preserve the folder and error text; do not reset data or substitute an unrelated key.')
section(3,'Activate your installation')
step('5. Sign in locally','Open the URL printed by the installer. Use the administrator email entered during setup and the initial password in bootstrap-password.txt. Protect that password and confirm access before removing the temporary file under your local policy.')
step('6. Export the installation request','Open Subscription. Under Install or renew a subscription choose Download licence request. The file is tec-epr-licence-request.json and contains only the request format and Installation ID.')
step('7. Request the approved licence','Submit an Installation licence request in the customer portal. The web form records the request; it does not upload installation JSON or issue a licence automatically. Send the request file through the agreed support channel to tlcoke@hotmail.com. Do not include patient records or passwords.')
step('8. Import the returned licence','TEC confirms the agreed organisation, installation, modules and expiry and returns a signed .teclicense. Under Licence file in Subscription choose the file, then select Verify and install. Do not edit the signed file.')
step('9. Check the result','Confirm Deployment: Customer installation, the original Installation ID, customer name, expiry and module entitlements. Payment or downloading the archive does not create this licence. Report unexpected values before clinical use.')
para('Keep the two trust identities distinct','HeadingTEC')
story.append(Preformatted('Publisher public-key SPKI SHA-256:\nb45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a\n\nLicence verification public-key SPKI SHA-256:\nfeba748a1b088c114f0e63e49d28b6203ca7d28c0b72e75aace3511379342f26',styles['CodeTEC']))
section(4,'Validate and operate safely')
step('10. Rehearse with synthetic records','Test administrator login and intended staff roles; create a synthetic clinician, a synthetic patient assigned to that clinician and an appointment. Read each record back. Check purchased modules, reports, attachments, audit and facility isolation before approving use.')
step('11. Complete site acceptance','A successful installation or licence activation does not validate every clinical function. The clinical owner must accept intended workflows, failure modes, report accuracy, downtime arrangements and any device/AI interfaces. Demo evaluations use synthetic data.')
step('12. Secure the host and staff access','Use named accounts with least privilege. Protect the host with supported updates, device encryption and endpoint protection. LAN or cloud access needs managed HTTPS, correct origins and reviewed firewall/support arrangements. Do not expose PostgreSQL.')
step('13. Protect recovery material','Follow the package\'s backup and restore instructions. Preserve database, uploads, installation identity and configuration together. Keep encrypted off-host copies and rehearse a restore in a separate empty environment. Record the site\'s recovery objectives and measured results.')
step('14. Renew before expiry','Request renewal before the displayed expiry. Do not assume a grace period or continued clinical access. Rehearse the site\'s continuity procedure for licence, network, power or host outages. Never regenerate the Installation ID to fix a licence.')
step('Critical recovery rule','Never delete a production volume, reset a live database or run docker compose down -v as a repair. Preserve evidence and use the agreed support and escalation procedure.')
section(5,'Requests and troubleshooting')
step('Track your requests','My software requests shows your own submissions. Received means recorded; reviewing means assessment is in progress; awaiting customer means follow-up is needed. Closed or rejected does not grant access. Contact support with the request ID when action is unclear.')
step('Payment and outright purchase','Payment-link requests are available per plan at /payments. A request is not an issued payment link or confirmed payment. Outright purchases and larger Enterprise deployments use private quotations. Implementation and monthly software fees are separate.')
step('Session expired','Choose Sign in securely and start a fresh sign-in. Keep the identity provider\'s recovery methods secure. Do not disable authentication or MFA as a workaround.')
step('No approved download','Check the account/request status, grant validity and recent sign-in. A registration, request or payment alone is not a download entitlement. Existing signed delivery links expire; request a new one through Customer access if permitted.')
step('Licence rejected','Check the original Installation ID, organisation, expiry, modules and bundled verification identity. Preserve the request and error text. Do not replace the public key with an arbitrary key or alter a signed licence.')
step('Clinical workflow or report issue','Stop the affected workflow and follow the organisation\'s clinical escalation/downtime process. Send non-sensitive error text and request/installation IDs to support. Do not send patient records, private keys, passwords or card security codes.')
step('Your commercial data','Export my request data provides your own commercial request history. It is not a patient-record export or complete identity-provider subject-access response.')
section(6,'Operator handoff and boundaries')
step('Appointed gateway operators','Complete recent authenticator verification through /account. Review customer requests at /admin/software-requests and update their workflow status using the protected form. Separate existing two-person approvals continue to govern download grants.')
step('Licence issuer','Use the protected owner-side issuer for agreed customer name, Installation ID, modules and expiry. Publisher signing and installation licensing use different keys. Keep private signing material off the gateway, customer package and source repository.')
step('Before wider deployment','Retain the exact release, source/image evidence and site acceptance record. Confirm independent security assessment, privacy and contractual obligations, clinical safety and regulatory applicability. Automated source checks do not replace these reviews.')
step('Support record','Record request ID, Installation ID, affected feature, time, non-sensitive symptoms and action taken. Preserve logs/evidence securely. Involve security/privacy and clinical leads where appropriate; do not erase records to clear an error.')
step('What this guide does not change','The signed clinical archive is unchanged. Full illustrated role/module training and protected automatic licence fulfilment remain separate work. No compliance certification, automatic approval or remote revocation of existing offline licences is implied.')
para('Thueman Coke Limited','HeadingTEC');para('32 Vivian Gardens, Watford, WD19 4PG, United Kingdom.<br/>Services may be arranged through Healthy Concept Medical Centre, 58 Barnet Street, Montego Bay, St James, Jamaica, under the applicable service agreement.')
SimpleDocTemplate(str(out),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=43,bottomMargin=62,title='TEC EPR 1.0.1 Customer Installation and Activation',author='Thueman Coke Limited').build(story,onFirstPage=footer,onLaterPages=footer)
doc=fitz.open(out);print('PDF pages:',len(doc))
for i,page in enumerate(doc):
 page.get_pixmap(matrix=fitz.Matrix(.7,.7)).save(f'tmp/pdfs/customer-guide-{i+1}.png')
from PIL import Image,ImageOps,ImageDraw
thumbs=[]
for i in range(len(doc)):
 im=Image.open(f'tmp/pdfs/customer-guide-{i+1}.png').convert('RGB');thumbs.append(im)
w,h=thumbs[0].size
montage=Image.new('RGB',(w*3,h*2),(210,215,223))
for i,im in enumerate(thumbs):montage.paste(im,((i%3)*w,(i//3)*h))
montage.save('tmp/pdfs/customer-guide-review.png')
