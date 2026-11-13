"""Production bootstrap tests only use isolated in-memory SQLite; no live credentials."""
import unittest
from sqlalchemy import create_engine, inspect, text
from customer_gateway.init_production import (
    initialize_empty, require_approval, EXPECTED_TABLES
)


def approved_env():
    return {
        "APP_ENV": "production",
        "GATEWAY_INITIALIZE_DB": "new-dedicated-production",
        "GATEWAY_DOWNLOADS_ENABLED": "false",
        "GATEWAY_RELEASE_APPROVED": "false",
        "GATEWAY_ENROLLMENT_SUBJECTS": "",
        "GATEWAY_PRODUCTION_BOOTSTRAP_APPROVAL_REF": "OWNER-GATEWAY-DB-PROVISION-20261113",
        "GATEWAY_ORIGIN": "https://customers.thuemancokelimited.com",
        "GATEWAY_EXPECTED_NEW_DATABASE_NAME": "tcl_gateway_production",
        "COMMERCIAL_DATABASE_URL": (
            "postgresql://dbowner:safe-synthetic-only@private-postgres.internal/tcl_gateway_production"
        ),
    }


class ProductionBootstrapTests(unittest.TestCase):
    def test_empty_isolated_database_creates_exact_gateway_schema(self):
        engine = create_engine("sqlite://")
        with engine.begin() as c:
            count = initialize_empty(c)
            self.assertEqual(count, len(EXPECTED_TABLES))
            self.assertGreaterEqual(count, 10)
            self.assertEqual(set(inspect(c).get_table_names()), EXPECTED_TABLES)
        with engine.connect() as c:
            for name in EXPECTED_TABLES:
                self.assertEqual(c.exec_driver_sql("SELECT COUNT(*) FROM " + name).scalar(), 0)
        engine.dispose()

    def test_nonempty_database_refused_without_new_tables(self):
        engine = create_engine("sqlite://")
        with engine.begin() as c:
            c.execute(text("CREATE TABLE existing_customer_data (id INTEGER)"))
            with self.assertRaisesRegex(RuntimeError, "not empty"):
                initialize_empty(c)
            self.assertEqual(inspect(c).get_table_names(), ["existing_customer_data"])
        engine.dispose()

    def test_wrong_environment_must_fail_closed(self):
        baseline = approved_env()
        self.assertEqual(require_approval(baseline).database, "tcl_gateway_production")
        changes = [
            ("APP_ENV", "staging"),
            ("GATEWAY_INITIALIZE_DB", "new-dedicated-staging"),
            ("GATEWAY_DOWNLOADS_ENABLED", "true"),
            ("GATEWAY_RELEASE_APPROVED", "true"),
            ("GATEWAY_ENROLLMENT_SUBJECTS", "user_fake"),
            ("GATEWAY_PRODUCTION_BOOTSTRAP_APPROVAL_REF", "test"),
            ("GATEWAY_ORIGIN", "https://tcl-customer-gateway-staging-staging.up.railway.app"),
            ("GATEWAY_EXPECTED_NEW_DATABASE_NAME", "other_db"),
            ("COMMERCIAL_DATABASE_URL", "postgresql://user:pass@host/railway"),
            ("COMMERCIAL_DATABASE_URL", "postgresql://user:pass@host/tcl_crm_production"),
            ("COMMERCIAL_DATABASE_URL", "postgresql://user:pass@host/gateway_test"),
        ]
        for name, value in changes:
            with self.subTest(name=name, value=value), self.assertRaises(RuntimeError):
                require_approval(dict(baseline, **{name: value}))

    def test_missing_explicit_flags_or_owner_approval_fails_closed(self):
        for name in ("GATEWAY_INITIALIZE_DB", "GATEWAY_RELEASE_APPROVED",
                     "GATEWAY_DOWNLOADS_ENABLED", "GATEWAY_PRODUCTION_BOOTSTRAP_APPROVAL_REF",
                     "GATEWAY_EXPECTED_NEW_DATABASE_NAME"):
            with self.subTest(name=name):
                data = approved_env()
                del data[name]
                with self.assertRaises(RuntimeError):
                    require_approval(data)


if __name__ == "__main__":
    unittest.main()
