import re
import os
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.pool import StaticPool
from customer_gateway.app import (Config, WorkOS, create_app, metadata, sessions,
                                  audit, FLOW_COOKIE, SESSION_COOKIE)


class Provider:
    def __init__(self):
        self.calls = []
        self.verified = True
        self.failure = False

    def exchange(self, code, verifier):
        self.calls.append((code, verifier))
        if self.failure:
            raise RuntimeError("sensitive-provider-response")
        return {"user": {"id": "user_synthetic", "email_verified": self.verified},
                "access_token": "must-not-be-stored", "refresh_token": "must-not-be-stored"}


class AuthTests(unittest.TestCase):
    def setUp(self):
        test_url = os.environ.get("GATEWAY_TEST_POSTGRES_URL")
        if test_url:
            from sqlalchemy.engine import make_url
            parsed = make_url(test_url)
            if parsed.host not in ("127.0.0.1", "localhost") or parsed.database != "gateway_test":
                raise RuntimeError("Only the dedicated local gateway_test database is allowed")
            self.engine = create_engine(test_url)
            metadata.drop_all(self.engine)
        else:
            self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                        connect_args={"check_same_thread": False})
        metadata.create_all(self.engine)
        self.config = Config("https://gateway.example", "client_synthetic", "sk_synthetic", True)
        self.provider = Provider()
        self.now = [10000]
        self.app = create_app(self.config, self.engine, self.provider, lambda: self.now[0])
        self.client = TestClient(self.app, base_url=self.config.origin, follow_redirects=False,
                                 raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        metadata.drop_all(self.engine)
        self.engine.dispose()

    def start(self):
        r = self.client.get("/auth/login")
        self.assertEqual(r.status_code, 303)
        q = parse_qs(urlsplit(r.headers["location"]).query)
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertEqual(q["redirect_uri"], [self.config.origin+"/auth/callback"])
        self.assertNotIn("sk_synthetic", r.headers["location"])
        return q["state"][0]

    def finish(self, state):
        return self.client.get("/auth/callback", params={"state": state, "code": "synthetic-code"})

    def count(self, table):
        with self.engine.connect() as c:
            return c.scalar(select(func.count()).select_from(table))

    def test_valid_login_is_audited_but_cannot_download(self):
        r = self.finish(self.start())
        self.assertEqual(r.status_code, 303)
        self.assertIn("HttpOnly", r.headers["set-cookie"])
        self.assertIn("Secure", r.headers["set-cookie"])
        self.assertIn("SameSite=lax", r.headers["set-cookie"])
        self.assertEqual(self.count(sessions), 1)
        self.assertEqual(self.count(audit), 1)
        with self.engine.connect() as c:
            row = c.execute(select(sessions)).mappings().one()
        self.assertNotEqual(row["token_hash"], self.client.cookies.get(SESSION_COOKIE))
        self.assertNotIn("must-not-be-stored", str(row))
        self.assertEqual(self.client.get("/account").status_code, 200)
        self.assertEqual(self.client.post("/api/downloads").status_code, 403)

    def test_callback_replay_is_rejected(self):
        state = self.start()
        self.assertEqual(self.finish(state).status_code, 303)
        self.assertEqual(self.finish(state).status_code, 400)
        self.assertEqual(len(self.provider.calls), 1)

    def test_cross_browser_state_rejected(self):
        state = self.start()
        self.client.cookies.clear()
        self.assertEqual(self.finish(state).status_code, 400)
        self.assertEqual(len(self.provider.calls), 0)

    def test_forged_state_and_expiry(self):
        state = self.start()
        self.assertEqual(self.finish("forged").status_code, 400)
        self.now[0] += 600
        self.assertEqual(self.finish(state).status_code, 400)
        self.assertEqual(self.count(sessions), 0)

    def test_unverified_email_and_provider_failure(self):
        self.provider.verified = False
        self.assertEqual(self.finish(self.start()).status_code, 401)
        self.provider.failure = True
        r = self.finish(self.start())
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("sensitive-provider-response", r.text)
        self.assertEqual(self.count(sessions), 0)

    def test_local_session_expires(self):
        self.finish(self.start())
        self.now[0] += 900
        self.assertEqual(self.client.get("/account").status_code, 401)

    def test_logout_origin_and_csrf_and_revocation(self):
        self.finish(self.start())
        old = self.client.cookies.get(SESSION_COOKIE)
        token = re.search("name='csrf' value='([^']+)'", self.client.get("/account").text)[1]
        self.assertEqual(self.client.post("/auth/logout", data={"csrf":token}).status_code, 403)
        headers = {"Origin": self.config.origin}
        self.assertEqual(self.client.post("/auth/logout", data={"csrf":"bad"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/auth/logout", data={"csrf":token}, headers=headers).status_code, 303)
        self.assertEqual(self.count(sessions), 0)
        self.client.cookies.set(SESSION_COOKIE, old)
        self.assertEqual(self.client.get("/account").status_code, 401)

    def test_audit_failure_rolls_back_session(self):
        state = self.start()
        audit.drop(self.engine)
        r = self.finish(state)
        self.assertEqual(r.status_code, 500)
        self.assertNotIn(SESSION_COOKIE, r.headers.get("set-cookie", ""))
        self.assertEqual(self.count(sessions), 0)

    def test_disabled_and_untrusted_host(self):
        disabled = create_app(Config(self.config.origin, "client_synthetic", "sk_synthetic"), self.engine)
        with TestClient(disabled, base_url=self.config.origin) as c:
            self.assertEqual(c.get("/auth/login").status_code, 503)
        self.assertEqual(self.client.get("/auth/login", headers={"host":"attacker.example"}).status_code, 400)
        self.assertEqual(self.client.post("/api/downloads").status_code, 401)

    def test_logout_page_policy_and_rejected_origins(self):
        callback = self.finish(self.start())
        self.assertEqual(callback.headers["referrer-policy"], "no-referrer")
        page = self.client.get("/account")
        self.assertEqual(page.headers["referrer-policy"], "same-origin")
        token = re.search("name='csrf' value='([^']+)'", page.text)[1]
        for origin in ("null", "https://attacker.example"):
            r = self.client.post("/auth/logout", data={"csrf": token}, headers={"Origin": origin})
            self.assertEqual(r.status_code, 403)
        self.assertEqual(self.count(sessions), 1)
        r = self.client.post("/auth/logout", data={"csrf": token}, headers={"Origin": self.config.origin})
        self.assertEqual(r.status_code, 303)
        self.assertEqual(self.count(sessions), 0)

    def test_branded_home_css_html_errors_and_machine_probes(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('<!doctype html>', home.text)
        self.assertIn('Thueman Coke Limited', home.text)
        self.assertIn('/assets/gateway.css', home.text)
        self.assertIn('noindex', home.text)
        css = self.client.get("/assets/gateway.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn('text/css', css.headers['content-type'])
        self.assertIn('style-src \'self\'', css.headers['content-security-policy'])
        self.assertIn('@media(max-width:720px)', css.text)
        for path, status in (("/account",401),("/does-not-exist",404),("/auth/logout",405)):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code,status)
                self.assertIn('text/html',response.headers['content-type'])
                self.assertIn('<!doctype html>',response.text)
                self.assertNotIn('{"detail":',response.text)
        self.assertTrue(self.client.get("/health").json()["ok"])
        self.assertTrue(self.client.get("/ready").json()["ready"])

    def test_logout_redirects_to_a_signed_out_landing_page(self):
        self.finish(self.start())
        account = self.client.get("/account")
        self.assertIn('Welcome to your account', account.text)
        token = re.search("name='csrf' value='([^']+)'", account.text)[1]
        result = self.client.post("/auth/logout", data={"csrf":token},
                                  headers={"origin": self.config.origin})
        self.assertEqual(result.status_code,303)
        self.assertEqual(result.headers['location'],'/signed-out')
        landing = self.client.get(result.headers['location'])
        self.assertEqual(landing.status_code,200)
        self.assertIn('You have signed out', landing.text)
        self.assertIn('single sign-on session may remain active', landing.text)
        self.assertIn('<!doctype html>', landing.text)
        self.assertEqual(self.count(sessions),0)

    def test_no_open_redirect_or_public_docs(self):
        state = self.start()
        r = self.client.get("/auth/callback", params={"state":state,"code":"code","next":"https://attacker.example"})
        self.assertEqual(r.headers["location"], "/account")
        for path in ("/docs", "/openapi.json"):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/").headers["cache-control"], "no-store")


class WorkOSAdapterTests(unittest.TestCase):
    def test_exchange_uses_pinned_endpoint_and_pkce(self):
        config = Config("https://gateway.example", "client_synthetic", "sk_synthetic")
        with patch("customer_gateway.app.httpx.Client") as factory:
            client = factory.return_value.__enter__.return_value
            client.post.return_value.json.return_value = {"user": {"id":"user_a"}}
            WorkOS(config).exchange("code", "verifier")
            factory.assert_called_once_with(timeout=10, follow_redirects=False)
            args, kwargs = client.post.call_args
            self.assertEqual(args[0], "https://api.workos.com/user_management/authenticate")
            self.assertEqual(kwargs["json"]["code_verifier"], "verifier")
            self.assertEqual(kwargs["json"]["client_id"], config.client_id)
            client.post.return_value.raise_for_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
