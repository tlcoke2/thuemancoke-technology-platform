"""Public catalogue and gated, minimal-business-data software interest intake.

No executable downloads, licence signing, clinical records or payment collection
occur in this module. Production intake requires explicit operator activation
and successful Cloudflare Turnstile verification.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .models import SalesLead

logger = logging.getLogger("thueman-coke-software-store")
router = APIRouter(prefix="/api/software", tags=["software-store"])

PRODUCT_ID = "tec-epr-clinic-edition"
PRIVACY_NOTICE_VERSION = "2026-10-29-software-interest-v1"

# Public catalog is informative, never a direct archive URL or licence entitlement.
CATALOG = [
    {
        "id": PRODUCT_ID,
        "name": "TEC EPR Clinic Edition",
        "version": "1.0.0",
        "publisher": "TEC Healthcare",
        "category": "Electronic patient records / clinic operations",
        "distribution": "Approved applicants only; verified signed package",
        "trial": "Application and eligibility review required",
        "downloadAvailable": False,
        "medicalDeviceCertified": False,
        "features": [
            "Patient records, consultations and appointments",
            "Clinical role controls and audit trails",
            "Prescriptions, laboratory and specimen workflows",
            "Dedicated customer-controlled local deployment",
            "Installation-bound signed subscription activation",
        ],
        "exclusions": [
            "No autonomous diagnosis or prescribing",
            "No blanket certification or interoperability claim",
            "No public installer or direct patient-data service",
        ],
    }
]


class SoftwareStoreSettings(BaseSettings):
    app_env: str = "development"
    software_leads_enabled: bool = False
    software_turnstile_site_key: str = ""
    software_turnstile_secret_key: str = ""
    software_turnstile_allowed_hosts: str = "thuemancokelimited.com,www.thuemancokelimited.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_store_settings() -> SoftwareStoreSettings:
    return SoftwareStoreSettings()


class SoftwareInterest(Base):
    """Business contact requests are isolated from clinical EPR databases."""

    __tablename__ = "software_interest_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(80), index=True)
    request_type: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(160))
    business_email: Mapped[str] = mapped_column(String(255), index=True)
    organisation: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100))
    contact_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy_notice_version: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class SoftwareInterestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_id: Literal["tec-epr-clinic-edition"]
    request_type: Literal["demo", "trial", "quotation"]
    full_name: str = Field(min_length=2, max_length=160)
    business_email: EmailStr
    organisation: str = Field(min_length=2, max_length=255)
    country: str = Field(min_length=2, max_length=100)
    contact_consent: Literal[True]
    marketing_opt_in: bool = False
    # Honeypot. Filled fields are silently dropped without data storage.
    website: str = Field(default="", max_length=500)
    turnstile_token: str = Field(default="", max_length=4096)


class SoftwareInterestReceipt(BaseModel):
    accepted: bool
    reference: str | None = None
    message: str


def intake_ready(config: SoftwareStoreSettings) -> bool:
    if not config.software_leads_enabled:
        return False
    if config.app_env == "production":
        return bool(config.software_turnstile_site_key and config.software_turnstile_secret_key)
    return True


def verify_turnstile(token: str, secret: str, allowed_hosts: str) -> bool:
    if not token or not secret:
        return False
    payload = urllib.parse.urlencode({"secret": secret, "response": token}).encode("utf-8")
    request = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = json.load(response)
        host = str(result.get("hostname") or "").casefold()
        accepted_hosts = {name.strip().casefold() for name in allowed_hosts.split(",") if name.strip()}
        return (
            result.get("success") is True
            and host in accepted_hosts
            and result.get("action") == "software_interest"
        )
    except (TimeoutError, ValueError, urllib.error.URLError, OSError):
        logger.warning("Software interest CAPTCHA validation unavailable")
        return False


@router.get("/catalog")
def get_catalog():
    return {"products": CATALOG}


@router.get("/registration-config")
def get_registration_config(config: SoftwareStoreSettings = Depends(get_store_settings)):
    return {
        "acceptingRequests": intake_ready(config),
        "turnstileSiteKey": config.software_turnstile_site_key if intake_ready(config) else "",
        "privacyNoticeVersion": PRIVACY_NOTICE_VERSION,
    }


@router.post("/interest", response_model=SoftwareInterestReceipt, status_code=status.HTTP_202_ACCEPTED)
def create_software_interest(
    form: SoftwareInterestCreate,
    db: Session = Depends(get_db),
    config: SoftwareStoreSettings = Depends(get_store_settings),
):
    if not intake_ready(config):
        raise HTTPException(status_code=503, detail="Software registration is not currently available.")
    if form.website:
        # Do not store honeypot contents or submit them to CRM.
        return SoftwareInterestReceipt(accepted=True, message="Request received for review.")
    if config.app_env == "production":
        if not verify_turnstile(
            form.turnstile_token,
            config.software_turnstile_secret_key,
            config.software_turnstile_allowed_hosts,
        ):
            raise HTTPException(status_code=400, detail="Verification was unsuccessful. Please retry.")
    reference = str(uuid.uuid4())
    record = SoftwareInterest(
        id=reference,
        product_id=form.product_id,
        request_type=form.request_type,
        full_name=form.full_name,
        business_email=str(form.business_email).lower(),
        organisation=form.organisation,
        country=form.country,
        contact_consent=True,
        marketing_opt_in=form.marketing_opt_in,
        privacy_notice_version=PRIVACY_NOTICE_VERSION,
    )
    lead = SalesLead(
        organisation=form.organisation,
        contact_name=form.full_name,
        contact_email=str(form.business_email).lower(),
        country=form.country,
        source="TCL software store",
        service_interest=f"TEC EPR Clinic Edition — {form.request_type}",
        stage="new",
        estimated_value=0,
        currency="JMD" if form.country.strip().casefold() == "jamaica" else "GBP",
        probability=10,
        next_action="Review EPR eligibility, privacy requirements and requested access; no automatic licence.",
        next_action_at=datetime.now(timezone.utc),
        notes=f"Software interest reference: {reference}; request: {form.request_type}",
        classification="review",
        archived=False,
    )
    try:
        db.add(record)
        db.add(lead)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Software registration database transaction failed")
        raise HTTPException(status_code=503, detail="Unable to save registration. Try again later.")
    return SoftwareInterestReceipt(
        accepted=True,
        reference=reference,
        message="Your request has been recorded for eligibility review. No trial or licence has been issued.",
    )
