"""Add only the customer request table to an initialized staging gateway."""
import os
from sqlalchemy import create_engine, inspect, text
try:
    from .app import metadata as auth_metadata
    from .mfa import metadata as access_metadata
    from .onboarding import metadata
except ImportError:
    from app import metadata as auth_metadata
    from mfa import metadata as access_metadata
    from onboarding import metadata


def migrate(c):
    inspector=inspect(c)
    expected=set(auth_metadata.tables)|set(access_metadata.tables)
    if set(inspector.get_table_names()) != expected or inspector.get_view_names():
        raise RuntimeError('Expected initialized gateway schema without customer requests; no changes made')
    for m in (auth_metadata,access_metadata):
        for table in m.tables.values():
            if {r['name'] for r in inspector.get_columns(table.name)} != set(table.c.keys()):
                raise RuntimeError('Existing gateway schema differs; no changes made')
    metadata.create_all(c)


def main():
    if (os.environ.get('APP_ENV')!='staging' or os.environ.get('GATEWAY_MIGRATE_ONBOARDING')!='add-customer-requests-staging'
        or os.environ.get('GATEWAY_ONBOARDING_ENABLED')=='true'):
        raise SystemExit('Explicit staging migration with onboarding disabled is required')
    url=os.environ.get('COMMERCIAL_DATABASE_URL','')
    if not url.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        raise SystemExit('Dedicated PostgreSQL required')
    url=url.replace('postgres://','postgresql+psycopg://',1).replace('postgresql://','postgresql+psycopg://',1)
    engine=create_engine(url,hide_parameters=True)
    with engine.begin() as c:
        c.execute(text('SELECT 1 FROM pg_advisory_xact_lock(82716393)'))
        migrate(c)
    print('PASS: Customer request table added; existing gateway records preserved.')

if __name__=='__main__': main()
