"""Explicit initialization for a NEW, dedicated staging database only."""
import os
from sqlalchemy import create_engine, inspect
from app import metadata

if os.environ.get("APP_ENV") != "staging" or os.environ.get("GATEWAY_INITIALIZE_DB") != "new-dedicated-staging":
    raise SystemExit("Initialization not authorized for this environment")
url = os.environ.get("COMMERCIAL_DATABASE_URL", "")
if not url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
    raise SystemExit("Dedicated PostgreSQL URL required")
url = url.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url, hide_parameters=True)
with engine.begin() as connection:
    inspector = inspect(connection)
    if inspector.get_table_names() or inspector.get_view_names():
        raise SystemExit("Database is not empty. No tables were changed.")
    metadata.create_all(connection)
print("PASS: Three gateway tables created in empty staging database.")
