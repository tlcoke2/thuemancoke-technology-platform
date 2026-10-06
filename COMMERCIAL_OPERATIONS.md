# TCL Commercial Operations

## Objective

Turn Thueman Coke Limited's website, prospecting activity and consulting capability into a measurable B2B sales pipeline.

## Operating model

```text
Market research
  -> Qualified lead
  -> Personalised outreach
  -> Follow-up
  -> Discovery meeting
  -> Proposal
  -> Won / Lost
  -> Delivery / recurring support
```

## Pipeline stages

| Stage | Default probability | Primary objective |
|---|---:|---|
| New Lead | 10% | Qualify fit and identify the correct contact |
| Contacted | 20% | Establish relevance and secure a response |
| Follow-up | 30% | Re-engage and clarify need |
| Meeting | 50% | Run discovery and define business value |
| Proposal | 70% | Agree scope, commercial terms and decision path |
| Won | 100% | Mobilise delivery and onboarding |
| Lost | 0% | Record reason and lessons learned |

Probabilities are planning assumptions and may be adjusted for a specific opportunity.

## Lead qualification

Prioritise organisations with a clear fit for one or more TCL capabilities:

- AI and intelligent automation
- applications and digital platforms
- data architecture and analytics
- cloud, servers and data-centre modernisation
- networks and connectivity
- cybersecurity and governance
- healthcare technology, EPR/LIMS and diagnostics
- websites, SEO and digital experience
- business promotion and digital advertising

High-fit sectors include healthcare/diagnostics, professional services, hospitality, logistics, education, charities/NGOs, SMEs and international projects.

## Outreach rules

- Use only publicly published business or executive contact details.
- Do not invent or infer private email addresses.
- Personalise every executive outreach message to a genuine business need.
- Avoid mass unsolicited sending.
- Prepare drafts for review when outreach is generated automatically.
- Include the TCL website and a clear, low-pressure next step.
- Do not promise guaranteed rankings, sales, leads or technical outcomes.

## Proposal workflow

1. Open the opportunity in the CRM.
2. Select **Proposal**.
3. Review and edit the executive summary, scope, amount and commercial terms.
4. Save the draft.
5. Use **Print / Save PDF** for a client-facing copy.
6. Mark the proposal **Sent** only after it has actually been issued.
7. The CRM moves the lead to Proposal stage and creates a five-day follow-up action.
8. Mark the proposal **Accepted** to move the opportunity to Won.
9. Mark it **Rejected** or **Expired** to close the opportunity as Lost.

Every proposal update is versioned in PostgreSQL.

## Forecasting

The CRM reports:

- total leads
- open pipeline value
- weighted pipeline value
- value of sent/accepted proposals
- won revenue
- conversion rate
- overdue actions
- actions due in the next seven days
- proposal counts by status

Weighted pipeline is:

```text
estimated opportunity value x stage probability
```

This is a management forecast, not guaranteed revenue.

## Advertising offer

Public page:

```text
https://thuemancokelimited.com/advertise.html
```

Current packages:

| Package | Price |
|---|---:|
| Business Visibility Starter | £195 one-off |
| Featured Promotion | £395/month |
| Growth Campaign | £750/month |
| Lead Generation Pro | £1,250/month |
| Sponsored Business Feature | from £125 |
| Campaign Landing Page | from £250 |
| Email Campaign Setup | from £295 |
| Paid advertising management | 15% of media spend, £250 minimum |

Media spend, hardware, licences, travel and supplier charges are separate unless explicitly included.

## Security and privacy

- CRM URL is not publicly linked from the main website.
- Search engines are instructed not to index the CRM.
- CRM API access requires `CRM_ADMIN_KEY`.
- The production key belongs only in Railway environment variables.
- Do not put production keys or passwords in GitHub, documentation or email.
- Exported CSV files may contain business contact data and should be handled as internal records.

## Weekly management cadence

### Monday
Review new prospects, prioritise outreach and set next actions.

### Wednesday
Review replies, move engaged leads to the correct stage and prepare discovery calls.

### Friday
Review proposal status, overdue actions, conversion metrics, won/lost outcomes and next week's priorities.

## Minimum CRM hygiene

Every active opportunity should have:

- a current stage
- a realistic estimated value
- a probability
- a next action
- a next-action date
- concise notes describing the latest position

No open opportunity should be left without a next action.
