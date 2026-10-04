import smtplib
from email.message import EmailMessage

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import ContactLead
from .schemas import ContactCreate, ContactResponse
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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
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
