"""One-time EMPTY production gateway schema initialization; never migrate staging or CRM.

This command is disabled by default and must run through the owner-controlled,
dedicated production Railway service console with separate approval. It does
not create customers, grants, administrators or licences.
"""
import os
from urllib.parse import urlsplit

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
try:
    from .app import metadata as auth_metadata
    from .mfa import metadata as access_metadata
    from .onboarding import metadata as onboarding_metadata
except ImportError:
    from app import metadata as auth_metadata
    from mfa import metadata as access_metadata
    from onboarding import metadata as onboarding_metadata

SCHEMAS = (auth_metadata, access_metadata, onboarding_metadata)
EXPECTED_TABLES = set().union(*(set(m.tables) for m in SCHEMAS))
FORBIDDEN_NAMES = {"postgres", "template0", "template1", "railway", "gateway_test"}


def initialize_empty(connection):
    """All-or-nothing: refuse any table, view, materialized view or FK collision."""
    inspector = inspect(connection)
    # PostgreSQL supports materialized-view introspection. In isolated SQLite
    # regressions the reflection API is intentionally unimplemented.
    materialized = (inspector.get_materialized_view_names()
                    if connection.dialect.name == "postgresql" else [])
    if inspector.get_table_names() or inspector.get_view_names() or materialized:
        raise RuntimeError("Production DB is not empty; no schema changed")
    # These are three independent, existing staging-proven metadata groups.
    # In production all are created inside one database transaction.
    for schema in SCHEMAS:
        schema.create_all(connection, checkfirst=False)
    inspector = inspect(connection)
    created = set(inspector.get_table_names())
    if created != EXPECTED_TABLES or inspector.get_view_names():
        raise RuntimeError("Expected dedicated gateway schema does not match")
    return len(created)


def require_approval(env):
    if env.get("APP_ENV") != "production" or env.get("GATEWAY_INITIALIZE_DB") != "new-dedicated-production":
        raise RuntimeError("Production database bootstrap explicitly disabled")
    for key in ("GATEWAY_DOWNLOADS_ENABLED", "GATEWAY_RELEASE_APPROVED"):
        if env.get(key) != "false":
            raise RuntimeError("Downloads must be explicitly OFF during schema bootstrap")
    if env.get("GATEWAY_ENROLLMENT_SUBJECTS", ""):
        raise RuntimeError("Production authenticator enrollment must not be enabled at bootstrap")
    ref = env.get("GATEWAY_PRODUCTION_BOOTSTRAP_APPROVAL_REF", "").strip()
    if (len(ref) < 12 or len(ref) > 240 or
            ref.lower().startswith(("test", "synthetic", "pending", "todo"))):
        raise RuntimeError("Missing genuine owner production database initialization approval")
    origin = env.get("GATEWAY_ORIGIN", "")
    u = urlsplit(origin)
    if (u.scheme != "https" or not u.hostname or
            not u.hostname.endswith(".thuemancokelimited.com") or
            u.hostname.startswith("staging.") or "staging" in u.hostname or
            u.path or u.query or u.fragment or u.username or u.password):
        raise RuntimeError("Dedicated production HTTPS customer gateway origin required")
    raw = env.get("COMMERCIAL_DATABASE_URL", "")
    try:
        db = make_url(raw.replace("postgres://", "postgresql+psycopg://", 1)
                          .replace("postgresql://", "postgresql+psycopg://", 1))
    except Exception:
        raise RuntimeError("Invalid dedicated production PostgreSQL URL") from None
    if (db.drivername != "postgresql+psycopg" or
            not db.username or not db.password or not db.host or not db.database or
            db.database.lower() in FORBIDDEN_NAMES or "staging" in db.database.lower() or
            "test" in db.database.lower() or "crm" in db.database.lower() or
            "epr" in db.database.lower()):
        raise RuntimeError("Dedicated commercial production DB credentials/name required")
    expected_db = env.get("GATEWAY_EXPECTED_NEW_DATABASE_NAME", "")
    if (not expected_db or expected_db != db.database or len(expected_db) > 128):
        raise RuntimeError("Production database-name owner attestation mismatch")
    return db


def main():
    try:
        url = require_approval(os.environ)
        engine = create_engine(url, hide_parameters=True, pool_pre_ping=True)
        try:
            with engine.begin() as conn:
                # Lock also prevents duplicate bootstrap attempts across processes.
                conn.execute(text("SELECT pg_advisory_xact_lock(82716401)"))
                count = initialize_empty(conn)
        finally:
            engine.dispose()
        print(f"PASS_EMPTY_DEDICATED_PRODUCTION_GATEWAY_SCHEMA_CREATED: {count} tables")
        print("Production downloads/release flags remain OFF. No user/grant/licence inserted.")
    except Exception:
        # No DSN, user, hostname, SQL arguments or private credentials in errors.
        print("HOLD_PRODUCTION_GATEWAY_BOOTSTRAP: dedicated DB/approval/schema check failed; no downloads enabled.")
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
