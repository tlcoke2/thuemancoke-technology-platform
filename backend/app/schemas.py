from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    organisation: str | None = Field(default=None, max_length=255)
    service: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    consent: bool


class ContactResponse(BaseModel):
    ok: bool
    id: int
    message: str
