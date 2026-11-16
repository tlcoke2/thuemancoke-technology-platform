"""Explicit first appointment of two verified Gateway operators. Never run at startup."""
import argparse
import os
import secrets
import time

import httpx
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.engine import make_url
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


def appoint(engine, owner_id, approver_id, approver_email, lookup, now, *, owner_email=None):
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
    if owner_email is not None and emails[0] != owner_email.strip().casefold():
        raise AppointmentError('Nominated owner email does not match')
    expected = {owner_id, approver_id}
    environment = 'production' if owner_email is not None else 'staging'
    roles = {owner_id: f'{environment}_owner_appointed',
             approver_id: f'{environment}_approver_appointed'}
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
        # The deployed MFA path records this legacy event name in both environments.
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


def production_target(env, url, owner_email):
    if (env.get('RAILWAY_SERVICE_NAME') != 'tcl-customer-gateway-production' or
        env.get('RAILWAY_ENVIRONMENT_NAME') != 'production' or
        env.get('GATEWAY_ORIGIN') != 'https://customers.thuemancokelimited.com' or
        env.get('GATEWAY_APPOINT_ADMINS') != 'confirmed-production-pair' or
        not env.get('GATEWAY_PRODUCTION_APPOINTMENT_APPROVAL_REF', '').strip() or
        env.get('GATEWAY_AUTH_ENABLED') != 'true' or
        env.get('GATEWAY_MFA_ENABLED') != 'true' or
        env.get('GATEWAY_DOWNLOADS_ENABLED') != 'false' or
        env.get('GATEWAY_RELEASE_APPROVED') != 'false' or
        not owner_email or not owner_email.strip()):
        raise AppointmentError('Require approved production Gateway with MFA enabled and downloads closed')
    try:
        target = make_url(url)
    except Exception:
        raise AppointmentError('Invalid dedicated production database URL') from None
    if (target.drivername != 'postgresql+psycopg' or
        target.host != 'tcl-gateway-postgres-production.railway.internal' or
        target.database != 'tcl_customer_gateway'):
        raise AppointmentError('Unexpected production Gateway database target')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-id', required=True)
    parser.add_argument('--owner-email')
    parser.add_argument('--approver-id', required=True)
    parser.add_argument('--approver-email', required=True)
    args = parser.parse_args()
    env = os.environ
    mode = env.get('APP_ENV')
    url = env.get('COMMERCIAL_DATABASE_URL', '')
    if not url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        raise SystemExit('Dedicated commercial PostgreSQL required')
    url = url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    try:
        if env.get('GATEWAY_ENROLLMENT_SUBJECTS', '').strip():
            raise AppointmentError('Close first-time enrollment before appointment')
        if mode == 'production':
            production_target(env, url, args.owner_email)
        elif (mode != 'staging' or env.get('GATEWAY_APPOINT_ADMINS') != 'confirmed-staging-pair'
              or args.owner_email is not None):
            raise AppointmentError('Require an explicit staging or production appointment')
        engine = create_engine(url, hide_parameters=True)
        try:
            if mode == 'production':
                with engine.connect() as conn:
                    if conn.scalar(text('SELECT current_database()')) != 'tcl_customer_gateway':
                        raise AppointmentError('Connected production database did not match')
            changed = appoint(engine, args.owner_id, args.approver_id, args.approver_email,
                              lambda subject: lookup_user(env['WORKOS_API_KEY'], subject), int(time.time()),
                              owner_email=args.owner_email)
        finally:
            engine.dispose()
    except AppointmentError as error:
        raise SystemExit(str(error)) from None
    except Exception:
        raise SystemExit('Appointment failed; inspect configuration/schema. No partial local transaction committed.') from None
    print(f'PASS: Both {mode} administrators appointed and audited.' if changed else
          'PASS: The same two audited appointments already exist; no changes made.')
    print('No tenant membership, download grant or licence was created.')

if __name__ == '__main__':
    main()
