"""Synthetic production gateway startup policy: no Railway, R2 or WorkOS calls."""
import os
import unittest
from unittest.mock import patch
from customer_gateway.app import from_environment


def prod_disabled():
    return {
        "APP_ENV": "production",
        "GATEWAY_ORIGIN": "https://customers.thuemancokelimited.com",
        "COMMERCIAL_DATABASE_URL":
            "postgresql://synthetic:synthetic@localhost/tcl_gateway_production",
        "WORKOS_CLIENT_ID": "client_synthetic-production",
        "WORKOS_API_KEY": "sk_synthetic-production",
        "GATEWAY_AUTH_ENABLED": "true",
        "GATEWAY_MFA_ENABLED": "true",
        "GATEWAY_DOWNLOADS_ENABLED": "false",
        "GATEWAY_RELEASE_APPROVED": "false",
        "GATEWAY_PRODUCTION_LAUNCH_APPROVED": "true",
        "GATEWAY_PRODUCTION_DATABASE_APPROVAL_REF": "OWNER-APPROVED-NEW-PRODUCTION-DB",
        "GATEWAY_PRODUCTION_WORKOS_APPROVAL_REF": "OWNER-APPROVED-PRODUCTION-WORKOS",
        "GATEWAY_ENROLLMENT_SUBJECTS": "",
    }


class ProductionLaunchGuards(unittest.TestCase):
    def test_production_gateway_may_start_with_mfa_and_downloads_off(self):
        env = prod_disabled()
        with patch.dict(os.environ, env, clear=True), patch(
            "customer_gateway.app.create_engine", return_value=object()
        ) as engine, patch("customer_gateway.app.create_app", return_value="safe-production-off") as factory:
            self.assertEqual(from_environment(), "safe-production-off")
            engine.assert_called_once()
            c = factory.call_args.args[0]
            self.assertEqual(c.environment, "production")
            self.assertTrue(c.enabled)
            self.assertTrue(c.mfa_enabled)
            self.assertFalse(c.downloads_enabled)
            self.assertFalse(c.release_approved)
            self.assertEqual(factory.call_args.kwargs["download_signer"], None)

    def test_missing_identity_infra_approvals_or_invalid_hostname_refuses_prod(self):
        base = prod_disabled()
        for name, value in [
            ("GATEWAY_PRODUCTION_LAUNCH_APPROVED", "false"),
            ("GATEWAY_PRODUCTION_DATABASE_APPROVAL_REF", "pending"),
            ("GATEWAY_PRODUCTION_WORKOS_APPROVAL_REF", "pending"),
            ("GATEWAY_ORIGIN", "https://tcl-customer-gateway-staging-staging.up.railway.app"),
            ("GATEWAY_ORIGIN", "http://customers.thuemancokelimited.com"),
            ("GATEWAY_AUTH_ENABLED", "false"),
            ("GATEWAY_MFA_ENABLED", "false"),
            ("COMMERCIAL_DATABASE_URL", ""),
        ]:
            with self.subTest(name=name, value=value), patch.dict(
                os.environ, dict(base, **{name: value}), clear=True
            ), patch("customer_gateway.app.create_engine") as engine:
                with self.assertRaises((RuntimeError, ValueError)):
                    from_environment()
                # For missing auth/MFA, create_engine can be called before
                # mandatory Config checks; no DB connection is made.
                self.assertFalse(engine.return_value.connect.called)

    def test_single_release_flag_or_without_signer_evidence_fails_closed(self):
        for flags in (("true", "false"), ("false", "true"), ("true", "true")):
            with self.subTest(flags=flags):
                env = prod_disabled()
                env["GATEWAY_DOWNLOADS_ENABLED"], env["GATEWAY_RELEASE_APPROVED"] = flags
                with patch.dict(os.environ, env, clear=True), patch(
                    "customer_gateway.app.create_engine"
                ) as engine, patch("customer_gateway.app.create_app") as app:
                    with self.assertRaisesRegex(RuntimeError, "SECURITY HOLD"):
                        from_environment()
                    engine.assert_not_called()
                    app.assert_not_called()


if __name__ == "__main__":
    unittest.main()
