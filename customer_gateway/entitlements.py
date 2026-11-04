"""Internal entitlement service. No HTTP route or identity bootstrap is exposed.

Caller supplies only a session hash; authority is reloaded from the database.
MFA elevations must be written by a separately reviewed provider verification flow.
No code in this module can create an elevation, administrator or membership.
"""
import secrets
from sqlalchemy import (MetaData, Table, Column, String, Integer, Boolean,
                        CheckConstraint, ForeignKey, insert, select, update)

metadata = MetaData()
tenants = Table('gateway_tenants', metadata,
    Column('id', String(64), primary_key=True),
    Column('active', Boolean, nullable=False))
memberships = Table('gateway_memberships', metadata,
    Column('tenant_id', String(64), ForeignKey('gateway_tenants.id'), primary_key=True),
    Column('subject', String(160), primary_key=True),
    Column('active', Boolean, nullable=False))
admins = Table('gateway_administrators', metadata,
    Column('subject', String(160), primary_key=True),
    Column('active', Boolean, nullable=False))
elevations = Table('gateway_mfa_elevations', metadata,
    Column('session_hash', String(64), primary_key=True),
    Column('subject', String(160), nullable=False),
    Column('verified_at', Integer, nullable=False),
    Column('expires', Integer, nullable=False),
    Column('provider_reference', String(160), nullable=False),
    CheckConstraint('expires > verified_at AND expires <= verified_at + 300'))
grants = Table('gateway_download_grants', metadata,
    Column('id', String(64), primary_key=True),
    Column('tenant_id', String(64), ForeignKey('gateway_tenants.id'), nullable=False),
    Column('release_id', String(80), nullable=False),
    Column('state', String(20), nullable=False),
    Column('proposer', String(160), nullable=False),
    Column('approver', String(160)),
    Column('contract_reference', String(160), nullable=False),
    Column('approval_reference', String(160), nullable=False),
    Column('starts', Integer, nullable=False),
    Column('expires', Integer, nullable=False),
    CheckConstraint("state IN ('pending','approved','revoked')"),
    CheckConstraint('expires > starts'),
    CheckConstraint("state != 'approved' OR (approver IS NOT NULL AND approver != proposer)"))
events = Table('gateway_entitlement_audit', metadata,
    Column('id', String(64), primary_key=True),
    Column('event', String(40), nullable=False),
    Column('actor', String(160), nullable=False),
    Column('grant_id', String(64), nullable=False),
    Column('created', Integer, nullable=False))

RELEASE = 'tec-epr-clinic-1.0.0'


class Denied(PermissionError):
    pass


class Entitlements:
    def __init__(self, engine, session_table, clock):
        self.engine, self.sessions, self.clock = engine, session_table, clock

    def _actor(self, c, session_hash, now):
        s = self.sessions
        # Locks serialize access with session/admin/elevation revocation on PostgreSQL.
        session = c.execute(select(s).where(s.c.token_hash == session_hash,
                    s.c.expires > now).with_for_update()).mappings().first()
        if not session:
            raise Denied('Active session required')
        subject = session['subject']
        admin = c.execute(select(admins).where(admins.c.subject == subject,
                    admins.c.active.is_(True)).with_for_update()).first()
        elevation = c.execute(select(elevations).where(
                    elevations.c.session_hash == session_hash,
                    elevations.c.subject == subject,
                    elevations.c.verified_at <= now,
                    elevations.c.verified_at > now - 300,
                    elevations.c.expires > now).with_for_update()).mappings().first()
        if not admin or not elevation or not elevation['provider_reference'].strip():
            raise Denied('Administrator with recent verified MFA required')
        return subject

    def _event(self, c, event, actor, grant_id, now):
        c.execute(insert(events).values(id=secrets.token_hex(16), event=event,
                  actor=actor, grant_id=grant_id, created=now))

    def propose(self, session_hash, *, tenant_id, release_id, starts, expires,
                contract_reference, approval_reference):
        if (release_id != RELEASE or type(starts) is not int or type(expires) is not int
                or starts >= expires or any(not isinstance(v, str) or not v.strip()
                or len(v) > 160 for v in (contract_reference, approval_reference))):
            raise Denied('Approved release and documented contract/approval required')
        now, grant_id = int(self.clock()), secrets.token_hex(16)
        with self.engine.begin() as c:
            actor = self._actor(c, session_hash, now)
            tenant = c.execute(select(tenants).where(tenants.c.id == tenant_id,
                       tenants.c.active.is_(True)).with_for_update()).first()
            if not tenant or expires <= now:
                raise Denied('Active tenant and unexpired interval required')
            c.execute(insert(grants).values(id=grant_id, tenant_id=tenant_id,
                release_id=release_id, state='pending', proposer=actor,
                contract_reference=contract_reference.strip(),
                approval_reference=approval_reference.strip(), starts=starts, expires=expires))
            self._event(c, 'grant_proposed', actor, grant_id, now)
        return grant_id

    def approve(self, session_hash, grant_id):
        now = int(self.clock())
        with self.engine.begin() as c:
            actor = self._actor(c, session_hash, now)
            g = c.execute(select(grants).where(grants.c.id == grant_id)
                          .with_for_update()).mappings().first()
            if not g or g['proposer'] == actor:
                raise Denied('A different administrator must approve')
            tenant = c.execute(select(tenants).where(tenants.c.id == g['tenant_id'],
                       tenants.c.active.is_(True)).with_for_update()).first()
            proposer = c.execute(select(admins).where(admins.c.subject == g['proposer'],
                       admins.c.active.is_(True)).with_for_update()).first()
            if not tenant or not proposer or g['expires'] <= now:
                raise Denied('Approval is no longer eligible')
            if g['state'] == 'approved' and g['approver'] == actor:
                return  # Idempotent retry; no duplicate approval event.
            if g['state'] != 'pending':
                raise Denied('Grant is not pending')
            result = c.execute(update(grants).where(grants.c.id == grant_id,
                       grants.c.state == 'pending').values(state='approved', approver=actor))
            if result.rowcount != 1:
                raise Denied('Grant changed; reload before approving')
            self._event(c, 'grant_approved', actor, grant_id, now)

    def revoke(self, session_hash, grant_id):
        now = int(self.clock())
        with self.engine.begin() as c:
            actor = self._actor(c, session_hash, now)
            g = c.execute(select(grants).where(grants.c.id == grant_id)
                          .with_for_update()).mappings().first()
            if not g:
                raise Denied('Unknown grant')
            if g['state'] == 'revoked':
                return
            c.execute(update(grants).where(grants.c.id == grant_id).values(state='revoked'))
            self._event(c, 'grant_revoked', actor, grant_id, now)
