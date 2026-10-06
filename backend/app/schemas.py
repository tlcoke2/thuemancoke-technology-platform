from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    organisation: str | None = Field(default=None, max_length=255)
    service: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    consent: bool
    website: str | None = Field(default=None, max_length=500)


class ContactResponse(BaseModel):
    ok: bool
    id: int
    message: str


SalesStage = Literal["new", "contacted", "follow_up", "meeting", "proposal", "won", "lost"]


class SalesLeadCreate(BaseModel):
    organisation: str = Field(min_length=2, max_length=255)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    sector: str | None = Field(default=None, max_length=160)
    country: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=160)
    service_interest: str | None = Field(default=None, max_length=255)
    stage: SalesStage = "new"
    estimated_value: float = Field(default=0, ge=0)
    currency: str = Field(default="GBP", min_length=3, max_length=8)
    probability: int = Field(default=10, ge=0, le=100)
    last_contacted_at: datetime | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=10000)


class SalesLeadUpdate(BaseModel):
    organisation: str | None = Field(default=None, min_length=2, max_length=255)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=500)
    sector: str | None = Field(default=None, max_length=160)
    country: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=160)
    service_interest: str | None = Field(default=None, max_length=255)
    stage: SalesStage | None = None
    estimated_value: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    probability: int | None = Field(default=None, ge=0, le=100)
    last_contacted_at: datetime | None = None
    next_action: str | None = Field(default=None, max_length=500)
    next_action_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=10000)


class SalesLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation: str
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    website: str | None
    sector: str | None
    country: str | None
    source: str | None
    service_interest: str | None
    stage: str
    estimated_value: float
    currency: str
    probability: int
    last_contacted_at: datetime | None
    next_action: str | None
    next_action_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PipelineSummary(BaseModel):
    total_leads: int
    by_stage: dict[str, int]
    open_pipeline_value: dict[str, float]
    weighted_pipeline_value: dict[str, float]
    overdue_actions: int
    actions_due_next_7_days: int
