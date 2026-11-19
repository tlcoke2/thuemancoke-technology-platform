# TEC EPR 1.0.1 — clinical user and administrator manual

Edition 1, 18 November 2026. Publisher: Thueman Coke Limited.
Support: tlcoke@hotmail.com. Use fictional records for training.

## Scope and evidence

This is a source-verified operating manual for the licence-enabled customer
installation, not a clinical protocol or a certification. It describes the screens
and controls in frontend revision `942c0833f30586c70e95b2a11b6d3b7d7eadab92`.
Backend revision: `630472009270c0097d5e86b6588b39edc3466e62`.
Archive SHA-256:
`c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059`.
It supplements the portal's installation guide at
https://customers.thuemancokelimited.com/help.

Screen paths below are relative to the installed application, **not** the customer
portal. Menus depend on role, facility and subscription. A hidden menu is not an
access-control test. Exact released-screen illustrations and supervised acceptance
of every workflow remain to be captured on the installed system. No reconstructed
screenshots are presented as actual evidence.

## 1. Start, sign in and prepare your clinic

1. Follow the installation guide and retain the installation's bootstrap details
   securely. Do not use a shared staff account.
2. Open the installed application, select Login (`/login`) and use your assigned
   account. Customer-portal/WorkOS credentials are separate from clinic accounts.
3. Ask the administrator to confirm your role and facility before viewing records.
   Check that you are using the intended clinic and the correct patient identity.
4. If access is denied, confirm the account, facility and active licence. Do not
   change database rows or enable owner mode to bypass access checks.
5. Sign out when leaving a shared workstation. Use workstation locking, supported
   updates, encrypted storage and the organisation's approved access policy.

The clinic administrator maintains staff and configuration; a clinician remains
responsible for clinical decisions. The organisation must define permitted duties
for Doctor, Nurse, Receptionist and Lab Technician before real use. The role list
in the UI is not a professional credential verification service.

## 2. Facilities, organisations and staff

Administration paths: `/admin`, `/admin/facilities`, `/admin/orgs`, `/admin/users`.
Use facilities and organisations belonging to the deployment. Facility membership
must be checked before allocating staff or entering patient records.

To add a doctor, open `/admin/doctors/add` (the same user-creation form used at
`/admin/users/add`). Under **Create New User**, enter Name, Email and Password;
select **Doctor** in Role and explicitly select the correct Facility. The form's
first facility may be preselected; do not accept it without checking. Select
**Register User**, then read the saved user back from the staff list. Confirm name,
role, email and facility and perform a separate sign-in as that user. Transfer
initial credentials securely; do not put passwords in support tickets.

Use `/admin/users/edit/:id` or `/admin/doctors/edit/:id` for the relevant account.
Verify the saved result after editing. On departure remove access under the
approved account procedure; preserve clinical authorship and audit evidence.
Do not delete a clinician simply to remove their historical association with care.

## 3. Patients and identity

1. Open `/patients` and check for an existing record using the organisation's
   approved identity checks. A similar name is insufficient to establish identity.
2. Open `/patients/add` (**Add New Patient**). Complete the patient details shown;
   review Gender, Ethnicity, Assigned Doctor and Facility as applicable.
3. Record Medical History and the available Vitals fields accurately. Check units
   against the field and local procedure. Smoking/alcohol selections are available.
4. Select **Save Patient**. Reopen the saved record from `/patients`, or its
   `/patients/view/:id` page. Compare identity, facility, assigned doctor and history.
5. Use `/patients/edit/:id` to correct an authorised error and read it back. Follow
   the clinic's correction policy; retain the reason through the approved process.

If a save fails, retain your entries securely and inspect the displayed error.
Search for the record before retrying to avoid duplicates. Never combine two
patients merely because their names match. Patient deletion/merging requires an
approved retention and correction procedure; it is not routine housekeeping.

## 4. Availability, appointments and calendar

Set availability at `/availability`: choose Doctor, Day of Week, Start Time and
End Time, submit using the form control and verify the saved schedule. The clinic
must confirm local timezone and daylight-saving handling on its installed system.

To schedule: open `/appointments/add` (**Schedule Appointment**), select Patient
and Doctor, enter **Date & Time** and Reason, then submit. The source converts the
entered date/time to UTC for submission. Open `/appointments` and `/calendar` to
confirm patient, doctor and the displayed local time. Test a UK clock-change date
before using UK scheduling. Use `/appointments/edit/:id` for authorised changes;
check the calendar again. Availability does not by itself prove a booking has been
reserved or that conflicting appointments are impossible.

If a dropdown is empty, check your facility/access and loading errors. Do not
create a second doctor or patient simply to work around a failed lookup.

## 5. Treatments and clinical notes

Start from the patient's record and open its treatment action:
`/patients/:patientId/treatments/add`. A missing patient ID stops the form; do not
substitute another patient's ID. On **Record Treatment**, choose Treating Doctor
and Treatment Code, then enter Diagnosis, Treatment and Outcome. Selecting a
configured treatment fills its name and price. Check **Treatment Cost (JMD)**.
Select **Save Treatment**, then reopen the patient's treatment history and check
patient, clinician, text, code and cost. `/treatments` lists treatments and
`/treatments/edit/:id` supports authorised editing.

The add workflow marks the treatment for automatic billing; check the billing
result before creating a manual duplicate. **Print Summary** prints a text summary;
check printer destination and collect the output promptly.

**Enable AI Suggestions / Get AI Suggestions** is optional. It sends diagnosis
text to the configured AI service. Keep it off for real patient information until
the organisation has approved that provider, data flow and use. Generated text
requires clinician review; it is not a diagnostic approval, validated prescribing
system or replacement for professional judgement.

## 6. Prescriptions

Open `/prescriptions/add` (**Add Prescription**). Select Patient and Prescribing
Doctor. Enter Prescription Code, Medicine, Dosage and Duration exactly as ordered
by the authorised prescriber. **Cost (Optional Override)** can be left empty for
a unique configured price. Select **Save Prescription**, reopen it in
`/prescriptions` and compare the patient, doctor, medicine, dose and duration with
the authorised order. Use `/prescriptions/edit/:id` for an approved correction.

Do not infer interaction, allergy, formulary or dose-range checking from the
presence of these fields. Verify allergies, contraindications, units and legal
prescribing authority through the clinic's approved clinical procedures. Free-text
entry and successful saving do not establish a clinically safe prescription.

## 7. Laboratory orders, results and reports

Open `/lab` to review tests. At `/lab/add`, select Patient and enter Test Name;
review the current user's Ordered By value. As applicable enter Test Code,
Specimen Type, Collection Date, Priority, Status, Result, Result Date, Reference
Range, Units, Cost and Notes. Priority/status choices come from the server. An
attachment can be PDF, PNG or JPEG; confirm the correct patient before attaching.
Select **Save Lab Test** and read it back from the list. Failed saves retain
entries; investigate the error rather than repeatedly submitting.

Result and report views are `/lab/results` and `/lab/view/:id`; editing is
`/lab/edit/:id`. A trained laboratory reviewer must verify patient identity,
specimen identity, analytical validity, units and reference intervals before any
clinical communication. Preserve the distinction between draft/unverified and
verified results. Check the rendered/downloaded report for identity, status,
readability and completeness. A PDF being generated is not analytical validation.

Cancellation, verified-result protection and amendment procedures require the
laboratory's approved policy. Do not bypass a refusal by deleting or modifying
underlying records. Escalate a wrong-patient or wrong-result incident immediately.

## 8. LIMS: instruments, QC and specimens

Laboratory administration: `/admin/lims`.

- **Laboratory Instruments** (`/admin/lims/instruments`): confirm the instrument
  inventory with the laboratory lead. Approved configuration, connectivity,
  calibration and interface validation must precede patient-result integration.
- **Quality Control Logs** (`/admin/lims/qc-logs`): use **+ Add QC Log** and the
  installed form, record the relevant instrument/control information and read
  back the saved entry. Apply the laboratory's release criteria; recording a QC
  log does not automatically establish that a run is acceptable.
- **Specimen Management** (`/admin/lims/specimens`): use **+ Add Specimen** with
  the correct clinical association. Confirm identity and collection/handling
  details under the laboratory SOP. In **Update specimen**, review Status and
  Storage location. **Disposed** and **Rejected** records become locked after
  saving. Check carefully before making either terminal change. A **Record
  locked** notice is a safeguard; escalate an authorised correction request.

The source confirms these routes and labels. Exact instrument/QC add-dialog
fields and complete interface commissioning require installed-screen acceptance;
this manual does not invent those controls or certify an analyser connection.

## 9. Billing, prices and supporting catalogues

At `/billing/add` (**Create Billing Record**), select Patient, enter Description
and Amount, select payment status (Unpaid, Pending, Paid or InsurancePending) and,
when applicable, method (Cash, Card, BankTransfer or Insurance). Select **Save
Bill**, reopen it in `/billing`, and compare amount, patient and status. Use
`/billing/edit/:id` for authorised corrections. A Paid entry is a record, not proof
of card settlement. Do not enter card numbers or CVV into clinical notes.

At `/pricing` (**Pricing Dashboard**), filter by Type (TREATMENT/LAB), Region
(JAMAICA/EUROPE) and Insurance (NONE/PRIVATE/PUBLIC/HMO) as appropriate. Review
code, type, region, insurance and amount before use. The dashboard labels prices
USD while the treatment form labels JMD: the deployment owner must resolve and
validate the site's currency interpretation before issuing real invoices. Do not
assume a currency conversion is performed.

Medicines, procedure codes, codes and pricing are licensed supporting capabilities.
This revision does not establish a dedicated route for every entitlement name.
Use only the installed, approved catalogue workflows; do not invent configuration
URLs or directly edit production tables.

## 10. Discharge and tasks

At `/discharge/add` (**Add Discharge Summary**), choose Patient and Doctor, enter
Discharge Summary and Discharge date, then **Submit**. Reopen from `/discharge`
and verify all values. The form retains entries on a save error; if clinicians or
patients fail to load, reload before submitting. `/discharge/edit/:id` supports
authorised edits. The clinician must approve the discharge content and follow-up
plan before it is communicated.

At `/tasks/add` (**Create New Task**), enter Title, Description and Due Date,
choose Assign To and Patient as appropriate, submit and verify it in `/tasks`.
Use `/tasks/edit/:id` for an authorised update. Tasks are workflow reminders;
urgent clinical escalation must use the clinic's immediate communication process.
Do not assume a saved task sends a notification or has been read by its assignee.

## 11. System settings, subscriptions and module access

At `/admin/settings`, review System Name, Logo URL, Dark Mode, Enable AI Assistant
and auto-billing settings for Treatments, Lab Tests and Prescriptions. Change
only an authorised configuration, verify it after saving and record its reason.
External logo/AI connections need the organisation's security/privacy assessment.

At `/admin/license` (**Subscription & Module Access**), confirm Deployment,
Installation ID, Customer, Expires and Module entitlements. Under **Install or
renew a subscription**, choose **Download licence request** and send that JSON
through the agreed support channel. It identifies the installation and is not a
private signing key. Obtain the issued `.teclicense`, choose Licence file or use
Subscription key, then **Verify and install**. Check the displayed organisation,
installation, expiry and modules. Keep the licence with the site's recovery
records. Never upload a private signing key to the application or customer portal.

An owner installation's bypass is not a customer subscription. A customer expiry
or mismatch must be corrected through an approved licence, not environment or
source changes. The licensed capabilities include patients, users, admin,
facilities, appointments, billing, discharges, lab, medicines, prescriptions,
pricing, procedurecodes, qc, settings, specimens, tasks, treatments, uploads,
lims, ai, export, labintegration, codes, availability and instruments.
Uploads/export/integration permissions do not imply a validated interface or
separate screen. Confirm any transfer's destination and minimum necessary data.

## 12. Errors, downtime and recovery

- Session expired: sign out and sign in through the installed application's login.
  Confirm saved state before repeating an interrupted submission.
- Access denied: ask the administrator to check role, facility and subscription;
  do not reuse another staff member's account.
- Save failed/blank dropdown: check the displayed error and connectivity, retain
  entries securely and read back before retry. Report module, time and an incident
  reference; remove patient information from routine support messages.
- Incorrect patient/result/dose: stop the affected workflow and use the clinical
  incident procedure. Preserve records, audit and the original report.
- Application outage: activate the clinic's paper/downtime process, maintain
  controlled patient identification and reconcile once service is safely restored.
- Recovery: restore an encrypted off-host backup only into an isolated test
  environment first. Verify schema, records, attachment availability, licence and
  access controls. Measure restoration time and recovered data age. Never reset a
  Railway volume or overwrite the retained database as a troubleshooting shortcut.

## 13. Training and acceptance record

Use a disposable installation and synthetic records. For every module record the
operator role/facility, release identity, steps, expected and observed result,
record IDs, safe screenshots and reviewer's decision. Include negative tests:
anonymous denial, wrong facility, expired licence, duplicate retry, failed save,
unauthorised edits, laboratory locked records and recovery. The owner-reported
successful doctor/patient/appointment chain and installed-licence test are retained
as evidence for those scenarios; they do not prove every module was exercised.

Clinical lead review, final screen illustrations, currency reconciliation and
installed testing of the remaining modules are outstanding acceptance actions.
