import re
import unittest
from unittest.mock import patch
from sqlalchemy import insert, select, delete, func
from fastapi.testclient import TestClient
from customer_gateway.app import Config, create_app, sessions, audit, digest, SESSION_COOKIE
from customer_gateway.mfa import metadata, elevations, attempts, challenges, WorkOSMFA
from customer_gateway.tests import test_auth as auth_tests
from customer_gateway.migrate_access import migrate


class MFAProvider:
    def __init__(self):
        self.valid = True
        self.error = False
        self.calls = 0
        self.during_verify = None

    def begin(self, subject):
        self.calls += 1
        if self.error: raise RuntimeError('secret-provider-detail')
        return 'auth_challenge_Test', 'auth_factor_Test', 10500

    def verify(self, challenge_id, factor_id, code):
        if self.during_verify: self.during_verify()
        if self.error: raise RuntimeError('secret-provider-detail')
        return self.valid


class MFATests(unittest.TestCase):
    # Reuse only setup/login helpers, not inherited test cases.
    setUp_auth = auth_tests.AuthTests.setUp
    tearDown_auth = auth_tests.AuthTests.tearDown
    start = auth_tests.AuthTests.start
    finish = auth_tests.AuthTests.finish
    count = auth_tests.AuthTests.count

    def setUp(self):
        self.setUp_auth()
        metadata.create_all(self.engine)
        self.client.close()
        self.mfa_provider = MFAProvider()
        self.config = Config(self.config.origin, 'client_synthetic', 'sk_synthetic', True, True)
        self.client = TestClient(create_app(self.config, self.engine, self.provider,
            lambda:self.now[0], self.mfa_provider), base_url=self.config.origin,
            follow_redirects=False, raise_server_exceptions=False)
        self.finish(self.start())
        self.csrf = re.search("name='csrf' value='([^']+)'", self.client.get('/account').text)[1]

    def tearDown(self):
        metadata.drop_all(self.engine)
        self.tearDown_auth()

    def post(self, path, **fields):
        return self.client.post(path, data={'csrf':self.csrf, **fields}, headers={'origin':self.config.origin})

    def begin(self):
        return self.post('/auth/mfa/start')

    def verify(self, code='123456'):
        return self.post('/auth/mfa/verify', code=code)

    def test_verified_session_and_no_privilege(self):
        self.assertEqual(self.begin().status_code, 303)
        page = self.client.get('/auth/mfa')
        self.assertEqual(page.headers['referrer-policy'], 'same-origin')
        self.assertEqual(self.verify().status_code, 303)
        with self.engine.connect() as c:
            row = c.execute(select(elevations)).mappings().one()
            self.assertEqual(row['expires'], 10300)
            self.assertEqual(row['session_hash'], digest(self.client.cookies.get(SESSION_COOKIE)))
        self.assertIn('verified for this session', self.client.get('/account').text)
        self.assertEqual(self.client.post('/api/downloads').status_code, 403)
        self.assertEqual(self.verify().status_code, 400)

    def test_failed_code_consumes_challenge(self):
        self.begin()
        self.mfa_provider.valid = False
        self.assertEqual(self.verify().status_code, 400)
        self.mfa_provider.valid = True
        self.assertEqual(self.verify().status_code, 400)
        self.assertEqual(self.count(elevations), 0)

    def test_origin_csrf_and_payload_limits(self):
        for origin in ('null','https://attacker.example'):
            self.assertEqual(self.client.post('/auth/mfa/start', data={'csrf':self.csrf},
                headers={'origin':origin}).status_code, 403)
        self.assertEqual(self.post('/auth/mfa/start', csrf='forged').status_code, 403)
        self.assertEqual(self.post('/auth/mfa/start', extra='x'*600).status_code, 413)
        self.assertEqual(self.mfa_provider.calls, 0)

    def test_subject_limit_survives_login(self):
        for _ in range(5): self.assertEqual(self.begin().status_code, 303)
        self.assertEqual(self.begin().status_code, 400)
        self.finish(self.start())
        self.csrf = re.search("name='csrf' value='([^']+)'", self.client.get('/account').text)[1]
        self.assertEqual(self.begin().status_code, 400)
        self.assertEqual(self.mfa_provider.calls, 5)

    def test_provider_failure_is_redacted_and_counted(self):
        self.mfa_provider.error = True
        response = self.begin()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('secret-provider-detail', response.text)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(attempts.c.count)), 1)
        self.assertEqual(self.count(elevations), 0)

    def test_logout_during_verification_prevents_elevation(self):
        self.begin()
        def revoke():
            with self.engine.begin() as c: c.execute(delete(sessions))
        self.mfa_provider.during_verify = revoke
        self.assertEqual(self.verify().status_code, 400)
        self.assertEqual(self.count(elevations), 0)

    def test_expired_challenge_and_session_binding(self):
        self.begin()
        self.now[0] = 10300
        self.assertEqual(self.verify().status_code, 400)
        self.now[0] = 10000
        self.begin()
        self.finish(self.start())
        self.csrf = re.search("name='csrf' value='([^']+)'", self.client.get('/account').text)[1]
        self.assertEqual(self.verify().status_code, 400)

    def test_audit_failure_rolls_back_elevation(self):
        self.begin()
        audit.drop(self.engine)
        self.assertEqual(self.verify().status_code, 500)
        self.assertEqual(self.count(elevations), 0)

    def test_impersonated_login_is_rejected(self):
        with patch.object(self.provider, 'exchange', return_value={
            'user':{'id':'user_synthetic','email_verified':True}, 'impersonator':{'email':'operator@example.com'}}):
            self.assertEqual(self.finish(self.start()).status_code, 401)

    def test_disabled_feature_never_calls_provider(self):
        config = Config(self.config.origin, 'client_synthetic', 'sk_synthetic', True, False)
        with TestClient(create_app(config, self.engine, self.provider, lambda:self.now[0], self.mfa_provider),
                        base_url=config.origin) as client:
            client.cookies.set(SESSION_COOKIE, self.client.cookies.get(SESSION_COOKIE))
            self.assertEqual(client.post('/auth/mfa/start').status_code, 503)
        self.assertEqual(self.mfa_provider.calls, 0)

    def test_elevation_cannot_outlive_session(self):
        from sqlalchemy import update
        with self.engine.begin() as c:
            c.execute(update(sessions).values(expires=10060))
        self.begin()
        self.assertEqual(self.verify().status_code, 303)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(elevations.c.expires)), 10060)

    def test_migration_rejects_unrelated_database(self):
        from sqlalchemy import text
        metadata.drop_all(self.engine)
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE unrelated (id INTEGER)'))
            with self.assertRaises(RuntimeError): migrate(c)
            c.execute(text('DROP TABLE unrelated'))
        self.assertEqual(self.count(sessions), 1)

    def test_migration_preserves_auth_and_refuses_repeat(self):
        metadata.drop_all(self.engine)
        with self.engine.begin() as c: migrate(c)
        self.assertEqual(self.count(sessions), 1)
        with self.assertRaises(RuntimeError):
            with self.engine.begin() as c: migrate(c)


class ProviderAdapterTests(unittest.TestCase):
    def test_only_bound_provider_challenge_is_accepted(self):
        provider = WorkOSMFA('sk_synthetic')
        factor = {'id':'auth_factor_Test', 'type':'totp', 'user_id':'user_Test', 'totp':{'secret':'never-retain'}}
        challenge = {'id':'auth_challenge_Test', 'authentication_factor_id':'auth_factor_Test',
                     'expires_at':'2026-11-01T12:00:00Z', 'code':'never-retain'}
        with patch.object(provider, '_request', side_effect=[{'data':[factor]}, challenge]) as call:
            result = provider.begin('user_Test')
            self.assertEqual(result[:2], ('auth_challenge_Test','auth_factor_Test'))
            self.assertNotIn('never-retain', str(result))
            self.assertEqual(call.call_args_list[0].args[1], '/user_management/users/user_Test/auth_factors')
        for response in ({'valid':'true','challenge':challenge},
                         {'valid':True,'challenge':{**challenge,'id':'auth_challenge_Other'}}):
            with patch.object(provider, '_request', return_value=response):
                self.assertFalse(provider.verify('auth_challenge_Test','auth_factor_Test','123456'))

    def test_foreign_or_missing_factor_rejected(self):
        from customer_gateway.mfa import MFAError
        provider = WorkOSMFA('sk_synthetic')
        for data in ([], [{'id':'auth_factor_Test','type':'totp','user_id':'user_Other'}]):
            with patch.object(provider,'_request',return_value={'data':data}), self.assertRaises(MFAError):
                provider.begin('user_Test')

    def test_https_adapter_disables_redirects(self):
        provider = WorkOSMFA('sk_synthetic')
        with patch('customer_gateway.mfa.httpx.Client') as factory:
            client = factory.return_value.__enter__.return_value
            provider._request('GET','/fixed')
            factory.assert_called_once_with(timeout=10, follow_redirects=False)
            self.assertEqual(client.request.call_args.args, ('GET','https://api.workos.com/fixed'))
            client.request.return_value.raise_for_status.assert_called_once()

if __name__ == '__main__': unittest.main()
