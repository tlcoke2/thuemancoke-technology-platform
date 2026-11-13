"""Fail-closed policy for a future authenticated private-download service.

Inputs must be server-loaded, never accepted as claims from a request body.
This module neither verifies JWTs nor signs URLs; no network or database effects.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class Denied(PermissionError):
    pass


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str
    email_verified: bool
    session_expires_at: datetime
    role: Role
    # Derived from validated IdP authentication context, never a client flag.
    mfa_verified: bool = False


@dataclass(frozen=True)
class Membership:
    issuer: str
    subject: str
    tenant_id: str
    active: bool


@dataclass(frozen=True)
class Grant:
    id: str
    tenant_id: str
    release_id: str
    state: str
    starts_at: datetime
    expires_at: datetime
    approval_reference: str
    contract_reference: str
    # Granting access does not generate or sign a software licence.


@dataclass(frozen=True)
class Release:
    id: str
    bucket: str
    object_key: str
    sha256: str
    bytes: int
    publisher_spki_sha256: str


CLINIC_1_0_0 = Release(
    id="tec-epr-clinic-1.0.0",
    bucket="tec-epr-private-releases",
    object_key="tec-epr/clinic-edition/1.0.0/TEC-EPR-Clinic-Edition-1.0.0-1d7024f7955a.tar.gz",
    sha256="e1c75bb867627cb60f0f5ff9737b602661550a15df75f5df52bf8c43835c8c0e",
    bytes=329965422,
    publisher_spki_sha256="6bd4d0bbe4f81fea83ab61875eca6a96c7f9310e765c3cbe89c05b7a28a0a733",
)


# Separate trusted publisher identities; 1.0.0 verification is not re-keyed.
PUBLISHER_101_SPKI_SHA256 = "b45e340ab53f4a50c2c38bfd8adfd481421568f346ab5cfb30a838d0855c269a"


@dataclass(frozen=True)
class DownloadDecision:
    grant_id: str
    tenant_id: str
    release: Release
    expires_at: datetime
    ttl_seconds: int


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Denied("Timezone-aware timestamps required")
    return value.astimezone(timezone.utc)


def authorize_download(*, enabled: bool, trusted_issuer: str, principal: Principal,
                       membership: Membership, grant: Grant, requested_tenant: str,
                       requested_release: str, now: datetime,
                       release_withdrawn: bool = True,
                       release: Release = CLINIC_1_0_0) -> DownloadDecision:
    """Return a <=5-minute decision, not an entitlement or download URL.

    Explicit withdrawal state is required: an omitted release status denies access.
    Call on every request with fresh membership/grant/release state. Do not cache.
    """
    if enabled is not True or release_withdrawn is not False:
        raise Denied("Downloads unavailable")
    if (not isinstance(release, Release) or release.bucket != "tec-epr-private-releases"
            or not release.object_key.startswith("tec-epr/clinic-edition/")
            or (release.id == "tec-epr-clinic-1.0.0" and
                release.publisher_spki_sha256 != CLINIC_1_0_0.publisher_spki_sha256)
            or (release.id == "tec-epr-clinic-1.0.1" and
                release.publisher_spki_sha256 != PUBLISHER_101_SPKI_SHA256)
            or release.id not in ("tec-epr-clinic-1.0.0", "tec-epr-clinic-1.0.1")):
        raise Denied("Unsigned or unreviewed release cannot be distributed")
    if not trusted_issuer or principal.issuer != trusted_issuer or not principal.subject:
        raise Denied("Untrusted identity")
    if principal.email_verified is not True:
        raise Denied("Verified email required")
    if principal.role not in (Role.CUSTOMER, Role.ADMIN):
        raise Denied("Unsupported role")
    if principal.role == Role.ADMIN and principal.mfa_verified is not True:
        raise Denied("Administrator MFA required")
    if (membership.active is not True or not requested_tenant
            or membership.issuer != principal.issuer
            or membership.subject != principal.subject
            or membership.tenant_id != requested_tenant
            or grant.tenant_id != requested_tenant):
        raise Denied("Tenant access denied")
    if (requested_release != release.id or grant.release_id != requested_release
            or grant.state != "approved" or not grant.id.strip()
            or not grant.approval_reference.strip() or not grant.contract_reference.strip()):
        raise Denied("Approved grant required")
    current = _utc(now)
    start, end = _utc(grant.starts_at), _utc(grant.expires_at)
    session_end = _utc(principal.session_expires_at)
    if not start <= current < end or session_end <= current:
        raise Denied("Grant or session is not active")
    ttl = min(300, int((end-current).total_seconds()), int((session_end-current).total_seconds()))
    if ttl < 1:
        raise Denied("Insufficient validity remaining")
    return DownloadDecision(grant.id, requested_tenant, release,
                            current + timedelta(seconds=ttl), ttl)
