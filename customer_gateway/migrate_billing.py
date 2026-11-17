"""Explicit additive migration for the dedicated commercial database; never reset."""
import os
from sqlalchemy import create_engine, inspect, text
try:
    from .billing import metadata
    from .app import metadata as auth
    from .mfa import metadata as access
    from .onboarding import metadata as onboarding
    from .customer_intake import metadata as intake
    from .appoint_admins import database_target, connected_target, PRODUCTION_SERVICE, PRODUCTION_ENVIRONMENT
except ImportError:
    from billing import metadata
    from app import metadata as auth
    from mfa import metadata as access
    from onboarding import metadata as onboarding
    from customer_intake import metadata as intake
    from appoint_admins import database_target, connected_target, PRODUCTION_SERVICE, PRODUCTION_ENVIRONMENT

BASE = (auth, access, onboarding, intake)

def migrate(c):
    inspector = inspect(c)
    baseline = set().union(*(set(m.tables) for m in BASE))
    actual = set(inspector.get_table_names())
    if actual not in (baseline, baseline | set(metadata.tables)) or inspector.get_view_names():
        raise RuntimeError('Unexpected gateway schema; no billing migration performed')
    for m in (*BASE, metadata):
        for name, table in m.tables.items():
            if name in actual and {v['name'] for v in inspector.get_columns(name)} != set(table.c.keys()):
                raise RuntimeError('Existing table differs; no columns replaced')
    metadata.create_all(c)


def main():
    if (os.getenv('APP_ENV') != 'production' or os.getenv('RAILWAY_SERVICE_ID') != PRODUCTION_SERVICE
            or os.getenv('RAILWAY_ENVIRONMENT_ID') != PRODUCTION_ENVIRONMENT
            or os.getenv('GATEWAY_BILLING_ENABLED', 'false') != 'false'
            or os.getenv('GATEWAY_MIGRATE_BILLING') != 'add-billing-ledger-production'):
        raise SystemExit('Explicit dedicated production billing migration required; checkout must be off')
    raw = os.getenv('COMMERCIAL_DATABASE_URL', '').replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    target = database_target(raw)
    if target.database != 'tcl_customer_gateway' or target.host != 'postgres-r2ez.railway.internal':
        raise SystemExit('Refusing any other database target')
    engine = create_engine(target, hide_parameters=True)
    with engine.begin() as c:
        connected_target(c, target)
        c.execute(text('SELECT pg_advisory_xact_lock(82716401)'))
        migrate(c)
    print('PASS billing ledger added; existing gateway and clinical records preserved')

if __name__ == '__main__':
    main()
