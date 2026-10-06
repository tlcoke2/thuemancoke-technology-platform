import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import ContactLead, SalesLead
from .schemas import (
    ContactCreate,
    ContactResponse,
    PipelineSummary,
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
