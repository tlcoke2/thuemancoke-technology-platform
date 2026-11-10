"""WorkOS TOTP verification and restricted first enrollment. Secrets are never persisted."""
import re
import secrets
from datetime import datetime

import httpx
from sqlalchemy import Column, Integer, String, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
try:
    from .entitlements import metadata, elevations
except ImportError:
    from entitlements import metadata, elevations

attempts = Table('gateway_mfa_limits', metadata,
    Column('subject', String(160), primary_key=True),
    Column('window_start', Integer, nullable=False),
    Column('count', Integer, nullable=False))
challenges = Table('gateway_mfa_challenges', metadata,
    Column('session_hash', String(64), primary_key=True),
    Column('subject', String(160), nullable=False),
    Column('challenge_id', String(160), nullable=False),
    Column('factor_id', String(160), nullable=False),
    Column('expires', Integer, nullable=False))


class MFAError(Exception):
    pass


def identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'[A-Za-z0-9]{1,128}', value):
        raise MFAError('Invalid provider identifier')
    return value


class WorkOSMFA:
    def __init__(self, api_key):
        self.api_key = api_key

    def _request(self, method, path, **kwargs):
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.request(method, 'https://api.workos.com' + path,
                headers={'Authorization': 'Bearer ' + self.api_key}, **kwargs)
            response.raise_for_status()
            return response.json()

    def begin(self, subject):
        subject = identifier(subject, 'user_')
        data = self._request('GET', f'/user_management/users/{subject}/auth_factors', params={'limit':100})
        # Only use the user's existing factor. Enrollment/reset remains in hosted AuthKit.
        factors = [f for f in data.get('data', []) if f.get('type') == 'totp']
        if len(factors) != 1 or data.get('list_metadata', {}).get('after'):
            raise MFAError('A single enrolled authenticator is required')
        factor = factors[0]
        owner = factor.get('user_id', factor.get('userId'))
        if owner is not None and owner != subject:
            raise MFAError('Factor identity mismatch')
        factor_id = identifier(factor.get('id'), 'auth_factor_')
        challenge = self._request('POST', f'/auth/factors/{factor_id}/challenge', json={})
        if challenge.get('authentication_factor_id') != factor_id:
            raise MFAError('Challenge identity mismatch')
        challenge_id = identifier(challenge.get('id'), 'auth_challenge_')
        expiry = datetime.fromisoformat(challenge['expires_at'].replace('Z', '+00:00'))
        if expiry.tzinfo is None:
            raise MFAError('Invalid challenge expiry')
        return challenge_id, factor_id, int(expiry.timestamp())

    def enroll(self, subject):
        subject = identifier(subject, 'user_')
        data = self._request('GET', f'/user_management/users/{subject}/auth_factors', params={'limit':100})
        if not isinstance(data.get('data'), list):
            raise MFAError('Could not confirm existing factors; setup refused')
        if data['data'] or (data.get('list_metadata') or {}).get('after'):
            raise MFAError('An authenticator already exists. Use Verify authenticator; setup cannot replace it.')
        result = self._request('POST', f'/user_management/users/{subject}/auth_factors',
            json={'type':'totp', 'totp_issuer':'TCL Customer Gateway', 'totp_user':subject})
        factor = result.get('authentication_factor', {})
        challenge = result.get('authentication_challenge', {})
        factor_id = identifier(factor.get('id'), 'auth_factor_')
        owner = factor.get('user_id', factor.get('userId'))
        if factor.get('type') != 'totp' or (owner is not None and owner != subject):
            raise MFAError('Unexpected enrollment identity; contact the operator')
        if challenge.get('authentication_factor_id') != factor_id:
            raise MFAError('Unexpected enrollment challenge; contact the operator')
        challenge_id = identifier(challenge.get('id'), 'auth_challenge_')
        expiry = datetime.fromisoformat(challenge['expires_at'].replace('Z', '+00:00'))
        if expiry.tzinfo is None:
            raise MFAError('Invalid enrollment expiry')
        details = factor.get('totp', {})
        key = details.get('secret', '')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Z2-7]{16,128}={0,6}', key):
            raise MFAError('Setup key unavailable; contact the operator')
        qr = details.get('qr_code', '')
        if not isinstance(qr, str) or len(qr) > 200000 or not re.fullmatch(r'data:image/png;base64,[A-Za-z0-9+/=]+', qr):
            qr = ''  # Manual entry remains available; never embed SVG/remote content.
        return challenge_id, factor_id, int(expiry.timestamp()), key, qr

    def verify(self, challenge_id, factor_id, code):
        identifier(challenge_id, 'auth_challenge_')
        data = self._request('POST', f'/auth/challenges/{challenge_id}/verify', json={'code':code})
        challenge = data.get('challenge', {})
        return (data.get('valid') is True and challenge.get('id') == challenge_id
                and challenge.get('authentication_factor_id') == factor_id)


class StepUp:
    def __init__(self, engine, session_table, audit_table, provider, clock):
        self.engine, self.sessions, self.audit = engine, session_table, audit_table
        self.provider, self.clock = provider, clock

    def _session(self, c, session_hash):
        s = self.sessions
        row = c.execute(select(s).where(s.c.token_hash == session_hash,
                s.c.expires > int(self.clock())).with_for_update()).mappings().first()
        if not row:
            raise MFAError('Sign in again')
        return row

    def _reserve(self, session_hash):
        now = int(self.clock())
        with self.engine.begin() as c:
            session = self._session(c, session_hash)
            subject = session['subject']
            # Subject-wide quota persists across sessions and replicas. Savepoint
            # handles simultaneous first requests without rolling back the outer txn.
            try:
                with c.begin_nested():
                    c.execute(insert(attempts).values(subject=subject, window_start=now, count=0))
            except IntegrityError:
                pass
            limit = c.execute(select(attempts).where(attempts.c.subject == subject)
                              .with_for_update()).mappings().one()
            start, count = limit['window_start'], limit['count']
            if now >= start + 600:
                start, count = now, 0
            if count >= 5:
                raise MFAError('Too many attempts; wait ten minutes')
            c.execute(update(attempts).where(attempts.c.subject == subject)
                      .values(window_start=start, count=count+1))
            c.execute(delete(challenges).where(challenges.c.session_hash == session_hash))
            c.execute(delete(elevations).where(elevations.c.session_hash == session_hash))
        return subject

    def begin(self, session_hash):
        subject = self._reserve(session_hash)
        # Quota is committed even when the provider fails. Never log its response.
        try:
            challenge_id, factor_id, expiry = self.provider.begin(subject)
        except Exception:
            raise MFAError('Could not start verification; check authenticator enrolment') from None
        with self.engine.begin() as c:
            session = self._session(c, session_hash)
            expiry = min(expiry, int(self.clock()) + 300, session['expires'])
            if expiry <= int(self.clock()):
                raise MFAError('Challenge expired; start again')
            # Concurrent starts leave at most one usable challenge for this session.
            c.execute(delete(challenges).where(challenges.c.session_hash == session_hash))
            c.execute(insert(challenges).values(session_hash=session_hash, subject=subject,
                      challenge_id=challenge_id, factor_id=factor_id, expires=expiry))

    def enroll(self, session_hash, allowed_subjects):
        with self.engine.begin() as c:
            session = self._session(c, session_hash)
            if session['subject'] not in allowed_subjects:
                raise MFAError('First-time setup is not enabled for this account')
            # Gateway sessions are issued for exactly 900 seconds, without refresh.
            if session['expires'] <= int(self.clock()) + 600:
                raise MFAError('Sign out and sign in again before setting up your authenticator')
        subject = self._reserve(session_hash)
        try:
            with self.engine.begin() as c:
                session = self._session(c, session_hash)
                if session['expires'] <= int(self.clock()) + 600:
                    raise MFAError('Sign in again before setting up your authenticator')
                # Serialize enrollment for the same subject across browser sessions.
                c.execute(select(attempts).where(attempts.c.subject == subject).with_for_update()).one()
                challenge_id, factor_id, expiry, key, qr = self.provider.enroll(subject)
                expiry = min(expiry, int(self.clock()) + 300, session['expires'])
                if expiry <= int(self.clock()):
                    raise MFAError('Setup challenge expired; contact the operator')
                c.execute(delete(challenges).where(challenges.c.session_hash == session_hash))
                c.execute(insert(challenges).values(session_hash=session_hash, subject=subject,
                    challenge_id=challenge_id, factor_id=factor_id, expires=expiry))
                c.execute(insert(self.audit).values(id=secrets.token_hex(16),
                    event='staging_mfa_enrollment_started', subject=subject, created=int(self.clock())))
            # Secret is returned only to this authenticated POST response, never DB/audit.
            return key, qr
        except MFAError:
            raise
        except Exception:
            # Provider creation cannot be rolled back with a local DB transaction.
            # Never retry automatically or delete/reset an existing factor.
            raise MFAError('Setup could not complete. Return to your account; contact the operator if a factor now exists.') from None

    def verify(self, session_hash, code):
        with self.engine.begin() as c:
            session = self._session(c, session_hash)
            # Consume before contacting provider; a failed attempt cannot be replayed.
            challenge = c.execute(delete(challenges).where(
                challenges.c.session_hash == session_hash,
                challenges.c.subject == session['subject'],
                challenges.c.expires > int(self.clock())).returning(challenges)).mappings().first()
        if not challenge:
            raise MFAError('Start a new verification')
        if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
            raise MFAError('Enter the six-digit authenticator code')
        try:
            valid = self.provider.verify(challenge['challenge_id'], challenge['factor_id'], code)
        except Exception:
            raise MFAError('Verification unavailable; start again') from None
        if valid is not True:
            raise MFAError('Code not accepted; start again')
        with self.engine.begin() as c:
            session = self._session(c, session_hash)
            now = int(self.clock())
            if challenge['expires'] <= now:
                raise MFAError('Challenge expired; start again')
            c.execute(delete(elevations).where(elevations.c.session_hash == session_hash))
            c.execute(insert(elevations).values(session_hash=session_hash,
                subject=session['subject'], verified_at=now, expires=min(now+300, session['expires']),
                provider_reference=challenge['challenge_id']))
            c.execute(insert(self.audit).values(id=secrets.token_hex(16), event='staging_mfa_verified',
                subject=session['subject'], created=now))
