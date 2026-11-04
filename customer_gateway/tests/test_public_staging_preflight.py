"""Public-only staging preflight tests: no real network or credentials."""
import unittest

from customer_gateway.public_staging_preflight import allowed_origin, assess

GOOD = "https://tcl-customer-gateway-staging-staging.up.railway.app"
HEADERS = {
    "cache-control":"no-store", "x-frame-options":"DENY",
    "x-content-type-options":"nosniff", "strict-transport-security":"max-age=31536000",
    "content-security-policy":"default-src 'none'; frame-ancestors 'none'",
}
HEALTH = {
    "ok":True, "environment":"staging", "service":"tcl-customer-gateway",
    "downloadsEnabled":False, "mfaStepUpEnabled":True,
    "authenticatorSetupAvailable":False, "customerOnboardingEnabled":True,
}

class PreflightTests(unittest.TestCase):
    def test_only_exact_staging_origin_allowed(self):
        self.assertTrue(allowed_origin(GOOD))
        for candidate in (
            "http://tcl-customer-gateway-staging-staging.up.railway.app",
            "https://example.com",
            "https://tcl-customer-gateway-staging-staging.up.railway.app:8443",
            GOOD+"/health",GOOD+"?redirect=https://evil.example",
            "https://user:password@tcl-customer-gateway-staging-staging.up.railway.app",
            "https://tcl-customer-gateway-stagingevil-staging.up.railway.app",
            "https://tcl-customer-gateway-staging-staging.up.railway.app.evil.example",
            "https://tcl-customer-gateway-staging-staging.up.railway.app/#secret",
        ):
            with self.subTest(origin=candidate):
                self.assertFalse(allowed_origin(candidate))
        self.assertFalse(allowed_origin(None))

    def test_safe_default_requirements_pass(self):
        calls=[]
        def fetch(_,path):
            calls.append(path)
            return (HEALTH if path=="/health" else {"ready":True}),HEADERS.copy()
        ok,problems=assess(GOOD,fetch)
        self.assertTrue(ok,problems)
        self.assertEqual(calls,["/health","/ready"])

    def test_downloads_enabled_or_enrollment_open_denied(self):
        for key,value in (
            ("downloadsEnabled",True),("authenticatorSetupAvailable",True),
            ("mfaStepUpEnabled",False),("environment","production"),("ok",False),
        ):
            with self.subTest(flag=key):
                body=dict(HEALTH,**{key:value})
                accepted,why=assess(GOOD,lambda _o,path:
                    (body if path=="/health" else {"ready":True},HEADERS))
                self.assertFalse(accepted)
                self.assertTrue(any(key in issue for issue in why))

    def test_headers_and_db_readiness_are_required(self):
        for key in HEADERS:
            with self.subTest(header=key):
                hdr=HEADERS.copy()
                hdr.pop(key)
                ok,issues=assess(GOOD,lambda _o,path:
                    (HEALTH if path=="/health" else {"ready":True},hdr))
                self.assertFalse(ok)
        ok,issues=assess(GOOD,lambda _o,path:
            (HEALTH if path=="/health" else {"ready":False},HEADERS))
        self.assertFalse(ok)
        self.assertTrue(any("/ready" in m for m in issues))

    def test_no_fetch_on_bad_origin(self):
        def should_not_run(_origin,_path):
            raise AssertionError("Unexpected external call")
        ok,problems=assess("https://www.thuemancokelimited.com",should_not_run)
        self.assertFalse(ok)
        self.assertIn("origin",problems[0].lower())

    def test_network_failures_redacted(self):
        def failed(_origin,_path):
            raise TimeoutError("sensitive diagnostic value")
        ok,problems=assess(GOOD,failed)
        self.assertFalse(ok)
        self.assertNotIn("sensitive diagnostic value",str(problems))


if __name__=="__main__":
    unittest.main()
