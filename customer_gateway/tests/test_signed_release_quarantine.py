"""Synthetic staging runtime quarantine: no network, secrets or database operations."""
import os
import unittest
from unittest.mock import patch

from customer_gateway.app import from_environment


def fake_environment():
    return {
        "APP_ENV":"staging",
        "COMMERCIAL_DATABASE_URL":"postgresql://synthetic:synthetic@localhost/no-connection",
        "GATEWAY_ORIGIN":"https://tcl-customer-gateway-staging-staging.up.railway.app",
        "WORKOS_CLIENT_ID":"client_synthetic",
        "WORKOS_API_KEY":"sk_synthetic",
        "GATEWAY_AUTH_ENABLED":"true",
        "GATEWAY_MFA_ENABLED":"true",
    }


class SignedReleaseCommercialHoldTests(unittest.TestCase):
    def test_neither_download_flag_can_be_enabled_on_signed_1_0_0(self):
        for left,right in (("true","false"),("false","true"),("true","true")):
            with self.subTest(downloads=left,approved=right):
                env=fake_environment()
                env.update(GATEWAY_DOWNLOADS_ENABLED=left,
                           GATEWAY_RELEASE_APPROVED=right)
                with patch.dict(os.environ,env,clear=True), patch(
                        "customer_gateway.app.create_engine") as engine, patch(
                        "customer_gateway.app.create_app") as webapp:
                    with self.assertRaisesRegex(RuntimeError,
                                                "SECURITY HOLD: TEC EPR Clinic Edition 1.0.0"):
                        from_environment()
                    engine.assert_not_called()
                    webapp.assert_not_called()

    def test_disabled_staging_service_still_initializes(self):
        env=fake_environment()
        env.update(GATEWAY_DOWNLOADS_ENABLED="false",
                   GATEWAY_RELEASE_APPROVED="false")
        sentinel=object()
        with patch.dict(os.environ,env,clear=True),patch(
                "customer_gateway.app.create_engine",return_value=sentinel) as engine,patch(
                "customer_gateway.app.create_app",return_value="staging-safe") as app:
            self.assertEqual(from_environment(),"staging-safe")
            engine.assert_called_once()
            self.assertIs(app.call_args.kwargs["download_signer"],None)

    def test_production_guard_remains_strict(self):
        env=fake_environment()
        env.update(APP_ENV="production",
                   GATEWAY_DOWNLOADS_ENABLED="false",
                   GATEWAY_RELEASE_APPROVED="false")
        with patch.dict(os.environ,env,clear=True),patch(
                "customer_gateway.app.create_engine") as engine:
            with self.assertRaisesRegex(RuntimeError, "staging-only"):
                from_environment()
            engine.assert_not_called()


if __name__=="__main__":
    unittest.main()
