"""Two-person creation of a new customer tenant, membership and download grant."""
import re
from sqlalchemy import (MetaData, Table, Column, String, Integer, insert, select, update, func)
try:
    from .entitlements import tenants, memberships, admins, grants, RELEASE, Denied
    from .mfa import identifier
except ImportError:
    from entitlements import tenants, memberships, admins, grants, RELEASE, Denied
    from mfa import identifier

metadata = MetaData()
requests = Table('gateway_customer_requests', metadata,
    Column('id', String(64), primary_key=True),
    Column('organisation', String(160), nullable=False),
    Column('subject', String(160), nullable=False),
    Column('email', String(254), nullable=False),
    Column('created', Integer, nullable=False))


class Onboarding:
    def __init__(self, entitlements, lookup):
        self.access, self.lookup = entitlements, lookup

    def _identity(self, subject, email):
        try:
            user = self.lookup(subject)
            valid = (user.get('id') == subject and user.get('email_verified') is True
                     and user.get('email', '').strip().casefold() == email)
        except Exception:
            raise Denied('Customer identity could not be verified; no access granted') from None
        if not valid:
            raise Denied('Customer ID and verified email must match')

    def propose(self, session_hash, *, request_id, organisation, subject, email,
                contract_reference, approval_reference, starts, expires):
        if not re.fullmatch('[a-f0-9]{32}', request_id):
            raise Denied('Invalid submission identifier')
        try:
            identifier(subject, 'user_')
        except Exception:
            raise Denied('Invalid customer identity') from None
        email = email.strip().casefold()
        organisation, contract_reference, approval_reference = (
            v.strip() for v in (organisation, contract_reference, approval_reference))
        if (not 3 <= len(email) <= 254 or '@' not in email or
            any(not v or len(v) > 160 for v in (organisation, contract_reference, approval_reference)) or
            type(starts) is not int or type(expires) is not int or
            not 0 <= starts < expires <= 2147483647):
            raise Denied('Complete organisation, contract, approval and valid UTC dates are required')
        now = int(self.access.clock())
        with self.access.engine.begin() as c:
            actor = self.access._actor(c, session_hash, now)
            old = c.execute(select(requests, grants.c.proposer, grants.c.starts, grants.c.expires,
                            grants.c.contract_reference, grants.c.approval_reference)
                            .join(grants, grants.c.id == requests.c.id)
                            .where(requests.c.id == request_id)).mappings().first()
            expected = dict(organisation=organisation, subject=subject, email=email, proposer=actor,
                            starts=starts, expires=expires, contract_reference=contract_reference,
                            approval_reference=approval_reference)
            if old:
                if any(old[k] != v for k,v in expected.items()):
                    raise Denied('Submission identifier already belongs to a different request')
                return request_id
            if expires <= now:
                raise Denied('The proposed grant has already expired')
            if c.scalar(select(func.count()).select_from(grants).where(
                    grants.c.proposer == actor, grants.c.state == 'pending')) >= 20:
                raise Denied('Review pending requests before submitting more')
            self._identity(subject, email)
            tenant_id = 'tenant_' + request_id
            # Pending requests create inactive records. Neither login nor proposal grants access.
            c.execute(insert(tenants).values(id=tenant_id, active=False))
            c.execute(insert(memberships).values(tenant_id=tenant_id, subject=subject, active=False))
            c.execute(insert(grants).values(id=request_id, tenant_id=tenant_id, release_id=self.access.release_id,
                state='pending', proposer=actor, contract_reference=contract_reference,
                approval_reference=approval_reference, starts=starts, expires=expires))
            c.execute(insert(requests).values(id=request_id, organisation=organisation,
                                            subject=subject, email=email, created=now))
            self.access._event(c, 'customer_proposed', actor, request_id, now)
        return request_id

    def approve(self, session_hash, request_id):
        now = int(self.access.clock())
        with self.access.engine.begin() as c:
            actor = self.access._actor(c, session_hash, now)
            g = c.execute(select(grants).where(grants.c.id == request_id).with_for_update()).mappings().first()
            r = c.execute(select(requests).where(requests.c.id == request_id).with_for_update()).mappings().first()
            if not g or not r or actor == g['proposer']:
                raise Denied('A different administrator must review this customer request')
            if g['state'] == 'approved' and g['approver'] == actor:
                return
            if g['state'] != 'pending' or g['expires'] <= now:
                raise Denied('Request is no longer pending or has expired')
            if not c.execute(select(admins).where(admins.c.subject == g['proposer'],
                              admins.c.active.is_(True)).with_for_update()).first():
                raise Denied('Proposing administrator is no longer active')
            self._identity(r['subject'], r['email'])
            tenant = c.execute(select(tenants).where(tenants.c.id == g['tenant_id']).with_for_update()).mappings().one()
            member = c.execute(select(memberships).where(memberships.c.tenant_id == g['tenant_id'],
                       memberships.c.subject == r['subject']).with_for_update()).mappings().one()
            if tenant['active'] or member['active']:
                raise Denied('Pending customer records changed; inspect before approval')
            c.execute(update(tenants).where(tenants.c.id == g['tenant_id']).values(active=True))
            c.execute(update(memberships).where(memberships.c.tenant_id == g['tenant_id'],
                       memberships.c.subject == r['subject']).values(active=True))
            c.execute(update(grants).where(grants.c.id == request_id).values(state='approved', approver=actor))
            self.access._event(c, 'customer_approved', actor, request_id, now)
