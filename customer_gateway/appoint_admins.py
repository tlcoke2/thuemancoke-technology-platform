"""Explicit first appointment of two confirmed staging operators. Never run at startup."""
import argparse
import os
import secrets
import time

import httpx
from sqlalchemy import create_engine, insert, select, text
try:
    from .app import audit
    from .entitlements import admins
    from .mfa import identifier
except ImportError:
    from app import audit
    from entitlements import admins
    from mfa import identifier


class AppointmentError(Exception):
    pass


def lookup_user(api_key, subject):
    identifier(subject, 'user_')
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        result = client.get('https://api.workos.com/user_management/users/' + subject,
                            headers={'Authorization':'Bearer ' + api_key})
        result.raise_for_status()
        return result.json()


def appoint(engine, owner_id, approver_id, approver_email, lookup, now):
    identifier(owner_id, 'user_')
    identifier(approver_id, 'user_')
    if owner_id == approver_id or not approver_email.strip():
        raise AppointmentError('Two distinct nominated identities are required')
    emails = []
    for subject in (owner_id, approver_id):
        try:
            user = lookup(subject)
        except Exception:
            raise AppointmentError('Provider identity check failed; no roles changed') from None
        if (user.get('id') != subject or user.get('email_verified') is not True
                or not isinstance(user.get('email'), str) or not user['email'].strip()):
            raise AppointmentError('A nominated identity is missing or unverified')
        emails.append(user['email'].strip().casefold())
    if emails[1] != approver_email.strip().casefold() or emails[0] == emails[1]:
        raise AppointmentError('Nominated approver email does not match, or identities share an email')
    expected = {owner_id, approver_id}
    roles = {owner_id:'staging_owner_appointed', approver_id:'staging_approver_appointed'}
    with engine.begin() as c:
        if c.dialect.name == 'postgresql':
            c.execute(text('SELECT 1 FROM pg_advisory_xact_lock(82716392)'))
        existing = c.execute(select(admins).with_for_update()).mappings().all()
        if existing:
            if {r['subject'] for r in existing} == expected and all(r['active'] for r in existing):
                for subject, event in roles.items():
                    if c.execute(select(audit.c.id).where(audit.c.subject == subject,
                               audit.c.event == event).limit(1)).first() is None:
                        raise AppointmentError('Existing appointments lack matching audit evidence')
                return False
            raise AppointmentError('Administrator records already exist; no replacement or reactivation permitted')
        for subject in expected:
            proof = c.execute(select(audit.c.id).where(audit.c.subject == subject,
                audit.c.event == 'staging_mfa_verified', audit.c.created <= now).limit(1)).first()
            if proof is None:
                raise AppointmentError('Both nominated users must complete gateway MFA first')
        for subject, event in roles.items():
            c.execute(insert(admins).values(subject=subject, active=True))
            c.execute(insert(audit).values(id=secrets.token_hex(16), event=event,
                                          subject=subject, created=now))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-id', required=True)
    parser.add_argument('--approver-id', required=True)
    parser.add_argument('--approver-email', required=True)
    args = parser.parse_args()
    if (os.environ.get('APP_ENV') != 'staging' or
        os.environ.get('GATEWAY_APPOINT_ADMINS') != 'confirmed-staging-pair' or
        os.environ.get('GATEWAY_ENROLLMENT_SUBJECTS', '').strip()):
        raise SystemExit('Require explicit staging appointment with first-time enrollment closed')
    url = os.environ.get('COMMERCIAL_DATABASE_URL', '')
    if not url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        raise SystemExit('Dedicated commercial PostgreSQL required')
    url = url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    try:
        engine = create_engine(url, hide_parameters=True)
        changed = appoint(engine, args.owner_id, args.approver_id, args.approver_email,
                          lambda subject: lookup_user(os.environ['WORKOS_API_KEY'], subject), int(time.time()))
    except AppointmentError as error:
        raise SystemExit(str(error)) from None
    except Exception:
        raise SystemExit('Appointment failed; inspect configuration/schema. No partial local transaction committed.') from None
    print('PASS: Both staging administrators appointed and audited.' if changed else
          'PASS: The same two audited appointments already exist; no changes made.')
    print('No tenant membership, download grant or licence was created.')

if __name__ == '__main__':
    main()
