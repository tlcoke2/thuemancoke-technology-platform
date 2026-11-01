"""Add empty access-control tables to the existing dedicated staging gateway DB."""
import os
from sqlalchemy import create_engine, inspect, text
try:
    from .app import metadata as auth_metadata
    from .mfa import metadata
except ImportError:
    from app import metadata as auth_metadata
    from mfa import metadata


def migrate(connection):
    inspector = inspect(connection)
    names = set(inspector.get_table_names())
    auth_names, access_names = set(auth_metadata.tables), set(metadata.tables)
    if inspector.get_view_names() or not auth_names.issubset(names) or names - auth_names - access_names:
        raise RuntimeError('Not the expected dedicated gateway schema; no changes made')
    for table in auth_metadata.tables.values():
        if {x['name'] for x in inspector.get_columns(table.name)} != set(table.c.keys()):
            raise RuntimeError('Authentication schema differs; no changes made')
    present = names & access_names
    if present:
        # Do not guess how to repair partial or previous access schemas.
        raise RuntimeError('Access tables already present; inspect migration history before proceeding')
    metadata.create_all(connection)


def main():
    if (os.environ.get('APP_ENV') != 'staging' or
        os.environ.get('GATEWAY_MIGRATE_ACCESS') != 'add-access-tables-staging' or
        os.environ.get('GATEWAY_MFA_ENABLED') == 'true'):
        raise SystemExit('Require explicit staging migration with MFA feature disabled')
    url = os.environ.get('COMMERCIAL_DATABASE_URL', '')
    if not url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        raise SystemExit('Dedicated PostgreSQL URL required')
    url = url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as c:
        c.execute(text('SELECT 1 FROM pg_advisory_xact_lock(82716391)'))
        migrate(c)
    print('PASS: Eight empty access/MFA tables added; existing authentication records preserved.')

if __name__ == '__main__':
    main()
