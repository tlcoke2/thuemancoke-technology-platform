import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import insert,select,func
from customer_gateway.tests.test_entitlements import EntitlementTests
from customer_gateway.app import Config,create_app,sessions,digest,SESSION_COOKIE
from customer_gateway.customer_intake import metadata,requests
from customer_gateway.entitlements import grants,events,elevations

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
    def test_payment_link_requests_preselect_plan_and_do_not_create_grants(self):
        from customer_gateway.customer_intake import INTENTS
        for index, intent in enumerate(('paylink_essentials','paylink_professional','paylink_enterprise')):
            self.assertLessEqual(len(intent),24)
            page=self.client.get('/customer/requests?intent='+intent)
            self.assertIn('value="'+intent+'" selected',page.text)
            self.assertEqual(self.submit(request_id=f'{index:032x}',intent=intent).status_code,303)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(requests)),3)
            self.assertEqual(c.scalar(select(func.count()).select_from(grants)),0)
        self.assertNotIn('<script>unsafe</script>',self.client.get('/customer/requests?intent=<script>unsafe</script>').text)

    def test_guest_payment_link_request_shows_registration_without_private_data(self):
        self.submit(organisation='PRIVATE ORGANISATION')
        self.client.cookies.clear()
        r=self.client.get('/customer/requests?intent=paylink_professional')
        self.assertEqual(r.status_code,200)
        self.assertIn('Payment link — Professional',r.text)
        self.assertIn('Create customer account',r.text)
        self.assertNotIn('PRIVATE ORGANISATION',r.text)
        self.assertEqual(self.submit(intent='paylink_professional').status_code,401)

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

    def become_admin(self, elevated=True):
        token=digest('admin-browser')
        with self.engine.begin() as c:
            c.execute(insert(sessions).values(token_hash=token,subject='user_a',csrf='synthetic',expires=10900))
            if elevated:
                c.execute(insert(elevations).values(session_hash=token,subject='user_a',verified_at=9990,expires=10290,provider_reference='synthetic-only'))
        self.client.cookies.set(SESSION_COOKIE,'admin-browser')

    def status(self,state='reviewing',expected='received'):
        return self.client.post('/admin/software-requests/'+'a'*32+'/status',data={'csrf':'synthetic','state':state,'expected_state':expected},headers={'Origin':'https://customers.example.com'},follow_redirects=False)

    def test_admin_status_requires_mfa_and_never_creates_grants(self):
        self.submit()
        self.assertEqual(self.status().status_code,403)
        self.become_admin()
        self.assertEqual(self.status().status_code,303)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(requests.c.state)),'reviewing')
            self.assertEqual(c.scalar(select(func.count()).select_from(grants)),0)
            self.assertEqual(c.scalar(select(func.count()).select_from(events).where(events.c.event=='software_request_reviewing')),1)

    def test_stale_and_terminal_updates_refused(self):
        self.submit(); self.become_admin()
        self.assertEqual(self.status('closed').status_code,303)
        self.assertEqual(self.status().status_code,409)
        self.assertEqual(self.status('reviewing','closed').status_code,409)
        self.assertEqual(self.status('approved','closed').status_code,400)

    def test_admin_without_elevation_denied(self):
        self.submit(); self.become_admin(False)
        self.assertEqual(self.status().status_code,403)

    def test_export_is_self_scoped_and_no_store(self):
        self.submit()
        with self.engine.begin() as c:
            c.execute(insert(requests).values(id='b'*32,subject='user_other',organisation='foreign-secret',country='UK',intent='demo',state='received',created=10000))
        r=self.client.get('/customer/requests/export')
        self.assertEqual(r.status_code,200)
        self.assertNotIn('foreign-secret',r.text)
        self.assertEqual(len(r.json()['requests']),1)
        self.assertEqual(r.headers['cache-control'],'no-store, no-transform')
        self.assertIn('attachment',r.headers['content-disposition'])
        self.assertEqual(self.client.get('/customer/requests/export?after=invalid').status_code,400)

    def test_audit_failure_rolls_back_request_creation(self):
        with patch('customer_gateway.entitlements.Entitlements._event',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.submit()
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(requests)),0)

    def test_security_headers_and_admin_form_referrer_policy(self):
        self.become_admin()
        r=self.client.get('/admin/software-requests')
        self.assertEqual(r.headers['referrer-policy'],'same-origin')
        self.assertEqual(r.headers['x-frame-options'],'DENY')
        self.assertEqual(r.headers['cross-origin-resource-policy'],'same-origin')
