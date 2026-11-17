import unittest
from fastapi.testclient import TestClient
from sqlalchemy import insert,select,func
from customer_gateway.tests.test_entitlements import EntitlementTests
from customer_gateway.app import Config,create_app,sessions,digest,SESSION_COOKIE
from customer_gateway.customer_intake import metadata,requests
from customer_gateway.entitlements import grants

class IntakeTests(unittest.TestCase):
    def setUp(self):
        EntitlementTests.setUp(self)
        metadata.create_all(self.engine)
        with self.engine.begin() as c:
            c.execute(insert(sessions).values(token_hash=digest('browser'),subject='user_customer',csrf='synthetic',expires=10900))
        self.client=TestClient(create_app(Config('https://customers.example.com','client_test','sk_test',True),self.engine,clock=lambda:self.now),base_url='https://customers.example.com')
        self.client.cookies.set(SESSION_COOKIE,'browser')
    def tearDown(self):
        metadata.drop_all(self.engine)
        EntitlementTests.tearDown(self)
    def submit(self,**changes):
        data=dict(csrf='synthetic',request_id='a'*32,organisation='Synthetic clinic',country='Jamaica',intent='demo')
        data.update(changes)
        return self.client.post('/customer/requests',data=data,headers={'Origin':'https://customers.example.com'},follow_redirects=False)
    def test_public_start_and_signup_hint(self):
        self.assertEqual(self.client.get('/start').status_code,200)
        r=self.client.get('/auth/login?screen_hint=sign-up',follow_redirects=False)
        self.assertIn('screen_hint=sign-up',r.headers['location'])
    def test_request_is_idempotent_and_does_not_grant_access(self):
        self.assertEqual(self.submit().status_code,303)
        self.assertEqual(self.submit().status_code,303)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(requests)),1)
            self.assertEqual(c.scalar(select(func.count()).select_from(grants)),0)
    def test_anonymous_csrf_origin_and_unknown_intent_denied(self):
        self.assertEqual(self.submit(csrf='wrong').status_code,403)
        self.assertEqual(self.submit(intent='admin').status_code,400)
        self.client.cookies.clear()
        self.assertEqual(self.submit().status_code,401)
    def test_daily_limit(self):
        for i in range(5): self.assertEqual(self.submit(request_id=f'{i:032x}').status_code,303)
        self.assertEqual(self.submit(request_id='b'*32).status_code,429)
    def test_other_customers_requests_are_hidden_and_admin_inbox_denied(self):
        self.submit(organisation='PRIVATE OTHER ORGANISATION')
        with self.engine.begin() as c:
            c.execute(insert(sessions).values(token_hash=digest('other'),subject='user_other',csrf='other',expires=10900))
        self.client.cookies.set(SESSION_COOKIE,'other')
        r=self.client.get('/customer/requests')
        self.assertNotIn('PRIVATE OTHER ORGANISATION',r.text)
        self.assertEqual(self.client.get('/admin/software-requests').status_code,403)
    def test_html_is_escaped_and_identifier_cannot_be_reused_for_changed_request(self):
        self.submit(organisation='<script>unsafe</script>')
        self.assertNotIn('<script>unsafe</script>',self.client.get('/customer/requests').text)
        self.assertEqual(self.submit(organisation='Different').status_code,409)
