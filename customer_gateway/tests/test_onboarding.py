import unittest
from unittest.mock import patch
from sqlalchemy import select, func, update
from fastapi.testclient import TestClient
from customer_gateway.tests import test_entitlements as fixture
from customer_gateway.entitlements import tenants, memberships, grants, admins, Denied, elevations
from customer_gateway.onboarding import metadata, requests, Onboarding
from customer_gateway.app import create_app, Config, sessions, SESSION_COOKIE, digest
from customer_gateway.migrate_onboarding import migrate


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        fixture.EntitlementTests.setUp(self)
        metadata.create_all(self.engine)
        self.email='customer@example.com'
        self.lookup=lambda subject: {'id':subject,'email':self.email,'email_verified':True}
        self.onboard=Onboarding(self.service,lambda subject:self.lookup(subject))
        self.request_id='a'*32

    def tearDown(self):
        metadata.drop_all(self.engine)
        fixture.EntitlementTests.tearDown(self)

    def propose(self, actor='user_a', **overrides):
        args=dict(request_id=self.request_id,organisation='Synthetic Clinic',subject='user_customer',
                  email='customer@example.com',contract_reference='synthetic-pilot',
                  approval_reference='synthetic-review',starts=10000,expires=12000)
        args.update(overrides)
        return self.onboard.propose(actor,**args)

    def count(self,table):
        with self.engine.connect() as c: return c.scalar(select(func.count()).select_from(table))

    def test_pending_membership_cannot_be_used_then_second_approval_activates(self):
        self.propose()
        with self.engine.connect() as c:
            self.assertFalse(c.scalar(select(memberships.c.active)))
            self.assertEqual(c.scalar(select(grants.c.state)),'pending')
        with self.assertRaises(Denied): self.onboard.approve('user_a',self.request_id)
        with self.assertRaises(Denied): self.service.approve('user_b',self.request_id)
        self.onboard.approve('user_b',self.request_id)
        self.onboard.approve('user_b',self.request_id)
        with self.engine.connect() as c:
            self.assertTrue(c.scalar(select(memberships.c.active)))
            self.assertEqual(c.scalar(select(grants.c.state)),'approved')
            self.assertEqual(c.scalar(select(grants.c.approver)),'user_b')

    def test_idempotent_proposal_cannot_be_rebound(self):
        self.propose()
        self.propose()
        self.assertEqual(self.count(requests),1)
        with self.assertRaises(Denied): self.propose(email='different@example.com')
        with self.assertRaises(Denied): self.propose(actor='user_b')

    def test_customer_and_expired_mfa_cannot_propose(self):
        with self.assertRaises(Denied): self.propose(actor='user_customer')
        self.now=10300
        with self.assertRaises(Denied): self.propose()
        self.assertEqual(self.count(requests),0)

    def test_mismatched_identity_and_provider_outage_create_no_records(self):
        self.email='different@example.com'
        with self.assertRaises(Denied): self.propose()
        def failure(subject): raise RuntimeError('secret-provider-data')
        self.lookup=failure
        with self.assertRaises(Denied): self.propose()
        self.assertEqual(self.count(requests),0)
        self.assertEqual(self.count(memberships),0)

    def test_identity_is_rechecked_before_approval(self):
        self.propose()
        self.email='changed@example.com'
        with self.assertRaises(Denied): self.onboard.approve('user_b',self.request_id)
        with self.engine.connect() as c: self.assertFalse(c.scalar(select(memberships.c.active)))

    def test_proposer_revocation_and_expired_grant_block_approval(self):
        self.propose(expires=10001)
        self.now=10001
        with self.assertRaises(Denied): self.onboard.approve('user_b',self.request_id)
        self.now=10000
        with self.engine.begin() as c:
            c.execute(update(admins).where(admins.c.subject=='user_a').values(active=False))
        with self.assertRaises(Denied): self.onboard.approve('user_b',self.request_id)

    def test_audit_failure_rolls_back_all_activation(self):
        self.propose()
        with patch.object(self.service,'_event',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.onboard.approve('user_b',self.request_id)
        with self.engine.connect() as c:
            self.assertFalse(c.scalar(select(memberships.c.active)))
            self.assertFalse(c.scalar(select(tenants.c.active).where(tenants.c.id=='tenant_'+self.request_id)))
            self.assertEqual(c.scalar(select(grants.c.state)),'pending')

    def test_revoked_pending_request_cannot_be_approved(self):
        self.propose()
        self.service.revoke('user_a',self.request_id)
        with self.assertRaises(Denied): self.onboard.approve('user_b',self.request_id)

    def test_audit_failure_on_proposal_leaves_no_customer_records(self):
        with patch.object(self.service,'_event',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.propose()
        self.assertEqual(self.count(requests),0)
        self.assertEqual(self.count(memberships),0)
        self.assertEqual(self.count(grants),0)

    def test_invalid_submission_dates_and_references(self):
        for values in ({'request_id':'bad'},{'expires':9999},{'starts':True},
                       {'contract_reference':' '},{'expires':2147483648},{'subject':'../other'}):
            with self.subTest(values=values),self.assertRaises(Denied): self.propose(**values)

    def test_additive_migration_preserves_existing_data_and_refuses_repeat(self):
        metadata.drop_all(self.engine)
        before=self.count(admins)
        with self.engine.begin() as c: migrate(c)
        self.assertEqual(self.count(admins),before)
        with self.assertRaises(RuntimeError):
            with self.engine.begin() as c: migrate(c)


class OnboardingUITests(unittest.TestCase):
    def setUp(self):
        OnboardingTests.setUp(self)
        self.config=Config('https://gateway.example','client_synthetic','sk_synthetic',True,True,(),True)
        with self.engine.begin() as c:
            for subject in ('user_a','user_b','user_customer'):
                c.execute(update(sessions).where(sessions.c.subject==subject).values(token_hash=digest(subject)))
                c.execute(update(elevations).where(elevations.c.subject==subject).values(session_hash=digest(subject)))
        self.client=TestClient(create_app(self.config,self.engine,clock=lambda:self.now,
            identity_lookup=self.lookup),base_url=self.config.origin,follow_redirects=False)
        self.client.cookies.set(SESSION_COOKIE,'user_a')

    def tearDown(self):
        self.client.close()
        OnboardingTests.tearDown(self)

    def form(self):
        return dict(csrf='synthetic',request_id='a'*32,organisation='Synthetic <Clinic>',
            subject='user_customer',email='customer@example.com',contract_reference='synthetic-contract',
            approval_reference='synthetic-review',starts='1970-01-01T02:40',expires='1970-01-02T00:00')

    def test_full_review_flow_and_customer_isolation(self):
        headers={'origin':self.config.origin}
        self.assertEqual(self.client.post('/admin/customers/propose',data=self.form(),headers=headers).status_code,303)
        url='/admin/customers/'+'a'*32+'/approve'
        self.assertEqual(self.client.post(url,data={'csrf':'synthetic'},headers=headers).status_code,403)
        self.client.cookies.set(SESSION_COOKIE,'user_b')
        page=self.client.get('/admin/customers')
        self.assertIn('Synthetic &lt;Clinic&gt;',page.text)
        self.assertEqual(page.headers['referrer-policy'],'same-origin')
        self.assertEqual(self.client.post(url,data={'csrf':'synthetic'},headers=headers).status_code,303)
        self.assertNotIn('Synthetic &lt;Clinic&gt;',self.client.get('/customer').text)
        self.client.cookies.set(SESSION_COOKIE,'user_customer')
        self.assertIn('Synthetic &lt;Clinic&gt;',self.client.get('/customer?subject=user_b').text)
        self.assertEqual(self.client.get('/admin/customers').status_code,403)
        self.client.cookies.set(SESSION_COOKIE,'user_a')
        self.assertNotIn('Synthetic &lt;Clinic&gt;',self.client.get('/customer?tenant=tenant_'+'a'*32).text)

    def test_expired_verification_has_recovery_and_creates_nothing(self):
        self.now=10300
        response=self.client.post("/admin/customers/propose",data=self.form(),headers={"origin":self.config.origin})
        self.assertEqual(response.status_code,403)
        self.assertIn("This action was not performed",response.text)
        self.assertIn("second tab",response.text)
        self.assertEqual(response.headers["cache-control"],"no-store")
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(requests)),0)

    def test_csrf_and_disabled_feature(self):
        self.assertEqual(self.client.post('/admin/customers/propose',data=self.form()).status_code,403)
        config=Config(self.config.origin,'client_synthetic','sk_synthetic',True,True)
        with TestClient(create_app(config,self.engine,clock=lambda:self.now),base_url=config.origin) as client:
            client.cookies.set(SESSION_COOKIE,'user_a')
            self.assertEqual(client.get('/admin/customers').status_code,503)

if __name__=='__main__': unittest.main()
