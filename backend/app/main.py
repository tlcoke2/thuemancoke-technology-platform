import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import ContactLead, ProposalVersion, SalesLead, SalesProposal
from .schemas import (
    ContactCreate,
    ContactResponse,
    PipelineSummary,
    ProposalResponse,
    ProposalUpdate,
    ProposalVersionResponse,
    RevenueForecast,
    SalesLeadCreate,
    SalesLeadResponse,
    SalesLeadUpdate,
)
from .settings import get_settings

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Thueman Coke Limited API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)

@app.get("/")
def root():
    return {
        "service": "Thueman Coke Limited API",
        "status": "online",
        "website": "https://thuemancokelimited.com",
        "health": "/api/health",
    }
    
@app.get("/api/health")
def health():
    return {"ok": True, "service": "thueman-coke-api", "environment": settings.app_env}


def send_notification(lead: ContactLead) -> None:
    required = [
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.contact_to_email,
    ]
    if not all(required):
        return

    msg = EmailMessage()
    msg["Subject"] = f"New TCL website enquiry — {lead.name}"
    msg["From"] = settings.from_email or settings.smtp_username
    msg["To"] = settings.contact_to_email
    msg["Reply-To"] = lead.email

    body = (
        "New website enquiry\n\n"
        f"Name: {lead.name}\n"
        f"Email: {lead.email}\n"
        f"Organisation: {lead.organisation or '-'}\n"
        f"Service: {lead.service or '-'}\n\n"
        "Message:\n"
        f"{lead.message}\n"
    )
    msg.set_content(body)

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)


@app.post("/api/contact", response_model=ContactResponse, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    if payload.website:
        return ContactResponse(ok=True, id=0, message="Your enquiry has been received.")

    if not payload.consent:
        raise HTTPException(status_code=400, detail="Consent is required.")

    lead = ContactLead(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        organisation=(payload.organisation or "").strip() or None,
        service=(payload.service or "").strip() or None,
        message=payload.message.strip(),
        consent=True,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    try:
        send_notification(lead)
    except Exception:
        pass

    return ContactResponse(
        ok=True,
        id=lead.id,
        message="Your enquiry has been received.",
    )


STAGE_PROBABILITY = {
    "new": 10,
    "contacted": 20,
    "follow_up": 30,
    "meeting": 50,
    "proposal": 70,
    "won": 100,
    "lost": 0,
}


def require_crm_key(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.crm_admin_key:
        raise HTTPException(status_code=503, detail="CRM is not configured.")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.crm_admin_key):
        raise HTTPException(status_code=401, detail="Invalid CRM credentials.")


@app.get("/api/crm/leads", response_model=list[SalesLeadResponse], dependencies=[Depends(require_crm_key)])
def list_sales_leads(stage: str | None = None, db: Session = Depends(get_db)):
    query = db.query(SalesLead)
    if stage:
        query = query.filter(SalesLead.stage == stage)
    return query.order_by(SalesLead.updated_at.desc()).all()


@app.post("/api/crm/leads", response_model=SalesLeadResponse, status_code=201, dependencies=[Depends(require_crm_key)])
def create_sales_lead(payload: SalesLeadCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["currency"] = data["currency"].upper()
    if data["stage"] != "new" and data["probability"] == 10:
        data["probability"] = STAGE_PROBABILITY[data["stage"]]
    if data.get("contact_email"):
        data["contact_email"] = str(data["contact_email"]).lower()

    lead = SalesLead(**data)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@app.patch("/api/crm/leads/{lead_id}", response_model=SalesLeadResponse, dependencies=[Depends(require_crm_key)])
def update_sales_lead(lead_id: int, payload: SalesLeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(SalesLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()
    if "contact_email" in data and data["contact_email"]:
        data["contact_email"] = str(data["contact_email"]).lower()
    if "stage" in data and data["stage"] and "probability" not in data:
        data["probability"] = STAGE_PROBABILITY[data["stage"]]

    for key, value in data.items():
        setattr(lead, key, value)

    lead.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)
    return lead


@app.get("/api/crm/summary", response_model=PipelineSummary, dependencies=[Depends(require_crm_key)])
def pipeline_summary(db: Session = Depends(get_db)):
    leads = db.query(SalesLead).all()
    by_stage = {stage: 0 for stage in STAGE_PROBABILITY}
    open_pipeline_value: dict[str, float] = {}
    weighted_pipeline_value: dict[str, float] = {}

    for lead in leads:
        by_stage[lead.stage] = by_stage.get(lead.stage, 0) + 1
        if lead.stage not in {"won", "lost"}:
            currency = (lead.currency or "GBP").upper()
            open_pipeline_value[currency] = round(
                open_pipeline_value.get(currency, 0) + float(lead.estimated_value or 0), 2
            )
            weighted_pipeline_value[currency] = round(
                weighted_pipeline_value.get(currency, 0)
                + (float(lead.estimated_value or 0) * int(lead.probability or 0) / 100),
                2,
            )

    now = datetime.now(timezone.utc)
    next_week = now + timedelta(days=7)
    overdue = (
        db.query(SalesLead)
        .filter(
            SalesLead.stage.notin_(["won", "lost"]),
            SalesLead.next_action_at.is_not(None),
            SalesLead.next_action_at < now,
        )
        .count()
    )
    due_next_7 = (
        db.query(SalesLead)
        .filter(
            SalesLead.stage.notin_(["won", "lost"]),
            SalesLead.next_action_at.is_not(None),
            SalesLead.next_action_at >= now,
            SalesLead.next_action_at <= next_week,
        )
        .count()
    )

    return PipelineSummary(
        total_leads=len(leads),
        by_stage=by_stage,
        open_pipeline_value=open_pipeline_value,
        weighted_pipeline_value=weighted_pipeline_value,
        overdue_actions=overdue,
        actions_due_next_7_days=due_next_7,
    )


STARTER_PIPELINE = [
    {
        "organisation": "Biomedical Caledonia Medical Laboratory Limited",
        "contact_name": "Helen Christian",
        "contact_email": "info@biomedicaljm.com",
        "website": "https://biomedicaljm.com",
        "sector": "Healthcare & Diagnostics",
        "country": "Jamaica",
        "source": "Public web research / company publication",
        "service_interest": "Cybersecurity, healthcare technology, integrations, resilience",
        "stage": "new",
        "estimated_value": 12000,
        "currency": "GBP",
        "probability": 10,
        "next_action": "Review and send personalised outreach draft; propose a cybersecurity and digital-health discovery call.",
        "notes": "Internal planning estimate only. Public company material identifies Helen Christian as CEO and describes ongoing cybersecurity programme work following a 2025 incident.",
    },
    {
        "organisation": "Microlabs Limited",
        "contact_name": "Trevor Campbell",
        "contact_email": "tcampbell@microlabs.limited",
        "website": "https://www.microlabs.limited",
        "sector": "Healthcare & Diagnostics",
        "country": "Jamaica",
        "source": "Public web research / JANAAC",
        "service_interest": "LIMS integration, cybersecurity, reporting, automation",
        "stage": "new",
        "estimated_value": 8000,
        "currency": "GBP",
        "probability": 10,
        "next_action": "Review and send personalised outreach draft; offer a laboratory systems and cybersecurity assessment.",
        "notes": "Internal planning estimate only. JANAAC lists Trevor Campbell as Managing Director and Microlabs as ISO 15189:2022 accredited.",
    },
    {
        "organisation": "Central Medical Laboratories Limited",
        "contact_name": "Audrey Clarke",
        "contact_email": "cmlabs@cwjamaica.com",
        "website": "https://www.cmlabsja.com",
        "sector": "Healthcare & Diagnostics",
        "country": "Jamaica",
        "source": "Public web research / JANAAC / company site",
        "service_interest": "LIS modernisation, integrations, analytics, cybersecurity",
        "stage": "new",
        "estimated_value": 10000,
        "currency": "GBP",
        "probability": 10,
        "next_action": "Review and send personalised outreach draft; position a phased LIS, analytics and resilience review.",
        "notes": "Internal planning estimate only. JANAAC lists Audrey Clarke as Managing Director. The company site describes a technology-driven LIS environment.",
    },
    {
        "organisation": "LTN Logistics International Company Limited",
        "contact_name": "Lorraine Thomas-Harris",
        "contact_email": "lorraine.harris@ltnlogisticscompany.com",
        "website": "https://www.ltnlogisticscompany.com",
        "sector": "Logistics & Supply Chain",
        "country": "Jamaica",
        "source": "Public web research / Jamaica Trade Portal / company profile",
        "service_interest": "Workflow automation, integrations, dashboards, cybersecurity",
        "stage": "new",
        "estimated_value": 12000,
        "currency": "GBP",
        "probability": 10,
        "next_action": "Review and send personalised outreach draft; propose an operations automation and technology discovery session.",
        "notes": "Internal planning estimate only. Public logistics sources identify Lorraine Thomas-Harris as CEO/President and describe technology integration and supply-chain services.",
    },
    {
        "organisation": "Abendana & Abendana",
        "contact_name": "Dane Anthony Marsh",
        "contact_email": "office@abendana.com",
        "website": "https://www.abendana.com",
        "sector": "Professional Services / Legal",
        "country": "Jamaica",
        "source": "Public web research / company site",
        "service_interest": "Cybersecurity, secure client workflows, cloud, digital platforms",
        "stage": "new",
        "estimated_value": 6000,
        "currency": "GBP",
        "probability": 10,
        "next_action": "Review and send personalised outreach draft; offer a secure legal-technology and client-workflow assessment.",
        "notes": "Internal planning estimate only. The firm site identifies Dane Anthony Marsh as Managing Partner and publishes office@abendana.com as its contact email.",
    },
]


@app.post("/api/crm/seed-starter", dependencies=[Depends(require_crm_key)])
def seed_starter_pipeline(db: Session = Depends(get_db)):
    created = 0
    skipped = 0
    created_ids: list[int] = []

    for item in STARTER_PIPELINE:
        existing = (
            db.query(SalesLead)
            .filter(
                SalesLead.organisation == item["organisation"],
                SalesLead.contact_email == item["contact_email"],
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        lead = SalesLead(**item)
        db.add(lead)
        db.flush()
        created_ids.append(lead.id)
        created += 1

    db.commit()
    return {
        "ok": True,
        "created": created,
        "skipped": skipped,
        "created_ids": created_ids,
        "message": "Starter pipeline loaded.",
    }



def proposal_scope_for(lead: SalesLead) -> str:
    interest = lead.service_interest or "technology modernisation and advisory"
    return (
        f"1. Discovery and current-state assessment focused on {interest}.\n"
        "2. Risk, opportunity and priority review covering people, process, systems and data.\n"
        "3. Recommended target architecture / solution approach and phased delivery roadmap.\n"
        "4. Implementation of the agreed priority work within the final signed scope.\n"
        "5. Testing, documentation, handover and appropriate knowledge transfer.\n\n"
        "Final deliverables, milestones, exclusions and third-party dependencies will be confirmed "
        "after discovery and before project commencement."
    )


def proposal_summary_for(lead: SalesLead) -> str:
    contact = f" for {lead.contact_name}" if lead.contact_name else ""
    return (
        f"Thueman Coke Limited proposes a focused technology engagement with {lead.organisation}{contact}. "
        f"The proposed work is centred on {lead.service_interest or 'technology improvement'}, with the aim "
        "of improving operational effectiveness, resilience, security and measurable business value. "
        "The engagement will be delivered in practical phases so priorities, risk and budget remain visible throughout."
    )


def proposal_terms_for(lead: SalesLead) -> str:
    return (
        f"Indicative professional-services value: {lead.currency} {float(lead.estimated_value or 0):,.2f}.\n"
        "This is a planning estimate until a final scope and quotation are approved.\n"
        "Third-party licences, hardware, advertising media spend, travel and supplier charges are excluded unless specifically stated.\n"
        "Payment milestones will be defined in the final quotation.\n"
        "No hidden charges: any material scope change or additional cost must be agreed before work proceeds.\n"
        "Proposal validity: 30 days from issue unless otherwise stated."
    )


def snapshot_proposal(proposal: SalesProposal, db: Session) -> ProposalVersion:
    latest = (
        db.query(func.max(ProposalVersion.version_number))
        .filter(ProposalVersion.proposal_id == proposal.id)
        .scalar()
    ) or 0
    version = ProposalVersion(
        proposal_id=proposal.id,
        version_number=int(latest) + 1,
        title=proposal.title,
        executive_summary=proposal.executive_summary,
        scope=proposal.scope,
        commercial_terms=proposal.commercial_terms,
        amount=float(proposal.amount or 0),
        currency=(proposal.currency or "GBP").upper(),
        status=proposal.status,
    )
    db.add(version)
    db.flush()
    return version


@app.post(
    "/api/crm/leads/{lead_id}/proposal",
    response_model=ProposalResponse,
    status_code=201,
    dependencies=[Depends(require_crm_key)],
)
def generate_sales_proposal(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(SalesLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    existing = (
        db.query(SalesProposal)
        .filter(SalesProposal.lead_id == lead_id, SalesProposal.status == "draft")
        .order_by(SalesProposal.updated_at.desc())
        .first()
    )
    if existing:
        version_count = (
            db.query(ProposalVersion)
            .filter(ProposalVersion.proposal_id == existing.id)
            .count()
        )
        if version_count == 0:
            snapshot_proposal(existing, db)
            db.commit()
        return existing

    now = datetime.now(timezone.utc)
    proposal = SalesProposal(
        lead_id=lead.id,
        title=f"Technology Services Proposal — {lead.organisation}",
        executive_summary=proposal_summary_for(lead),
        scope=proposal_scope_for(lead),
        commercial_terms=proposal_terms_for(lead),
        amount=float(lead.estimated_value or 0),
        currency=(lead.currency or "GBP").upper(),
        status="draft",
        valid_until=now + timedelta(days=30),
    )
    db.add(proposal)
    db.flush()
    snapshot_proposal(proposal, db)
    db.commit()
    db.refresh(proposal)
    return proposal


@app.get(
    "/api/crm/proposals",
    response_model=list[ProposalResponse],
    dependencies=[Depends(require_crm_key)],
)
def list_sales_proposals(lead_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(SalesProposal)
    if lead_id is not None:
        query = query.filter(SalesProposal.lead_id == lead_id)
    return query.order_by(SalesProposal.updated_at.desc()).all()


@app.get(
    "/api/crm/proposals/{proposal_id}/versions",
    response_model=list[ProposalVersionResponse],
    dependencies=[Depends(require_crm_key)],
)
def list_proposal_versions(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.get(SalesProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return (
        db.query(ProposalVersion)
        .filter(ProposalVersion.proposal_id == proposal_id)
        .order_by(ProposalVersion.version_number.desc())
        .all()
    )


@app.patch(
    "/api/crm/proposals/{proposal_id}",
    response_model=ProposalResponse,
    dependencies=[Depends(require_crm_key)],
)
def update_sales_proposal(proposal_id: int, payload: ProposalUpdate, db: Session = Depends(get_db)):
    proposal = db.get(SalesProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    data = payload.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"]:
        data["currency"] = data["currency"].upper()

    for key, value in data.items():
        setattr(proposal, key, value)

    proposal.updated_at = datetime.now(timezone.utc)

    lead = db.get(SalesLead, proposal.lead_id)
    status = data.get("status")
    if lead and status == "sent":
        lead.stage = "proposal"
        lead.probability = STAGE_PROBABILITY["proposal"]
        lead.next_action = "Follow up on proposal."
        lead.next_action_at = datetime.now(timezone.utc) + timedelta(days=5)
        lead.updated_at = datetime.now(timezone.utc)
    elif lead and status == "accepted":
        lead.stage = "won"
        lead.probability = STAGE_PROBABILITY["won"]
        lead.next_action = "Begin onboarding and project mobilisation."
        lead.next_action_at = datetime.now(timezone.utc) + timedelta(days=2)
        lead.updated_at = datetime.now(timezone.utc)
    elif lead and status in {"rejected", "expired"}:
        lead.stage = "lost"
        lead.probability = STAGE_PROBABILITY["lost"]
        lead.next_action = "Record outcome and lessons learned."
        lead.next_action_at = None
        lead.updated_at = datetime.now(timezone.utc)

    db.flush()
    snapshot_proposal(proposal, db)
    db.commit()
    db.refresh(proposal)
    return proposal



@app.get(
    "/api/crm/forecast",
    response_model=RevenueForecast,
    dependencies=[Depends(require_crm_key)],
)
def revenue_forecast(db: Session = Depends(get_db)):
    leads = db.query(SalesLead).all()
    proposals = db.query(SalesProposal).all()

    by_stage = {stage: 0 for stage in STAGE_PROBABILITY}
    open_pipeline_value: dict[str, float] = {}
    weighted_pipeline_value: dict[str, float] = {}
    proposal_value: dict[str, float] = {}
    won_value: dict[str, float] = {}
    proposals_by_status: dict[str, int] = {
        "draft": 0,
        "sent": 0,
        "accepted": 0,
        "rejected": 0,
        "expired": 0,
    }

    open_opportunities = 0
    won_count = 0
    lost_count = 0

    for lead in leads:
        by_stage[lead.stage] = by_stage.get(lead.stage, 0) + 1
        currency = (lead.currency or "GBP").upper()
        value = float(lead.estimated_value or 0)

        if lead.stage == "won":
            won_count += 1
            won_value[currency] = round(won_value.get(currency, 0) + value, 2)
        elif lead.stage == "lost":
            lost_count += 1
        else:
            open_opportunities += 1
            open_pipeline_value[currency] = round(
                open_pipeline_value.get(currency, 0) + value, 2
            )
            weighted_pipeline_value[currency] = round(
                weighted_pipeline_value.get(currency, 0)
                + (value * int(lead.probability or 0) / 100),
                2,
            )

    for proposal in proposals:
        proposals_by_status[proposal.status] = proposals_by_status.get(proposal.status, 0) + 1
        if proposal.status in {"sent", "accepted"}:
            currency = (proposal.currency or "GBP").upper()
            proposal_value[currency] = round(
                proposal_value.get(currency, 0) + float(proposal.amount or 0), 2
            )

    closed = won_count + lost_count
    conversion_rate = round((won_count / closed * 100), 1) if closed else 0.0

    return RevenueForecast(
        total_leads=len(leads),
        open_opportunities=open_opportunities,
        won_count=won_count,
        lost_count=lost_count,
        conversion_rate=conversion_rate,
        by_stage=by_stage,
        open_pipeline_value=open_pipeline_value,
        weighted_pipeline_value=weighted_pipeline_value,
        proposal_value=proposal_value,
        won_value=won_value,
        proposals_by_status=proposals_by_status,
    )
