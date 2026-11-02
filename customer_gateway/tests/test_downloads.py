import unittest
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from sqlalchemy import insert,select,update,func
from fastapi.testclient import TestClient
from customer_gateway.tests import test_entitlements as fixture
from customer_gateway.entitlements import grants,memberships,tenants,events,elevations
from customer_gateway.app import Config,create_app,sessions,digest,SESSION_COOKIE
from customer_gateway.downloads import Downloads,R2Signer,R2_ENDPOINT,EXPECTED_ETAG
from customer_gateway.download_policy import Denied,CLINIC_1_0_0


class Signer:
    def __init__(self): self.calls=[]; self.checked=0; self.fail=False
    def check(self):
        self.checked+=1
        if self.fail: raise RuntimeError('synthetic storage failure')
    def sign(self,decision):
        self.calls.append(decision)
        return R2_ENDPOINT+'/private-synthetic?token=never-audit-this'


class DownloadTests(unittest.TestCase):
    def setUp(self):
        fixture.EntitlementTests.setUp(self)
        with self.engine.begin() as c:
            c.execute(insert(memberships).values(tenant_id='tenant_a',subject='user_customer',active=True))
            c.execute(insert(grants).values(id='grant_test',tenant_id='tenant_a',release_id=CLINIC_1_0_0.id,
                state='approved',proposer='user_a',approver='user_b',starts=9990,expires=11000,
                contract_reference='synthetic-contract',approval_reference='synthetic-review'))
        self.signer=Signer()
        self.downloads=Downloads(self.service,self.signer,True,True)

    tearDown=fixture.EntitlementTests.tearDown

    def issue(self,subject='user_customer'):
        return self.downloads.issue(subject,'grant_test')

    def test_authorized_download_audits_without_storing_url(self):
        url,decision=self.issue()
        self.assertEqual(decision.ttl_seconds,300)
        self.assertEqual(len(self.signer.calls),1)
        with self.engine.connect() as c:
            rows=c.execute(select(events)).mappings().all()
            self.assertEqual(rows[0]['event'],'download_link_issued')
            self.assertNotIn('never-audit-this',str(rows))

    def test_disabled_withdrawn_or_no_membership_never_signs(self):
        with self.assertRaises(Denied): Downloads(self.service,self.signer,False,True).issue('user_customer','grant_test')
        with self.assertRaises(Denied): Downloads(self.service,self.signer,True,False).issue('user_customer','grant_test')
        with self.assertRaises(Denied): self.issue('user_a')
        self.assertEqual(self.signer.checked,0)

    def test_admin_membership_requires_recent_mfa(self):
        with self.engine.begin() as c:
            c.execute(insert(memberships).values(tenant_id='tenant_a',subject='user_a',active=True))
        self.issue('user_a')
        self.now=10300
        with self.assertRaises(Denied): self.issue('user_a')
        self.assertEqual(len(self.signer.calls),1)

    def test_revoked_expired_and_inactive_membership_deny(self):
        with self.engine.begin() as c: c.execute(update(grants).values(state='revoked'))
        with self.assertRaises(Denied): self.issue()
        with self.engine.begin() as c: c.execute(update(grants).values(state='approved',expires=10000))
        with self.assertRaises(Denied): self.issue()
        with self.engine.begin() as c:
            c.execute(update(grants).values(expires=11000))
            c.execute(update(memberships).values(active=False))
        with self.assertRaises(Denied): self.issue()
        self.assertEqual(self.signer.checked,0)

    def test_customer_cannot_download_another_tenants_grant(self):
        with self.engine.begin() as c:
            c.execute(update(tenants).where(tenants.c.id=='tenant_b').values(active=True))
            c.execute(insert(grants).values(id='foreign',tenant_id='tenant_b',release_id=CLINIC_1_0_0.id,
                state='approved',proposer='user_a',approver='user_b',starts=9990,expires=11000,
                contract_reference='synthetic-other',approval_reference='synthetic-other-review'))
        with self.assertRaises(Denied): self.downloads.issue('user_customer','foreign')
        self.assertEqual(self.signer.checked,0)

    def test_lifetime_cannot_outlive_session(self):
        with self.engine.begin() as c:
            c.execute(update(sessions).where(sessions.c.subject=='user_customer').values(expires=10023))
        _,decision=self.issue()
        self.assertEqual(decision.ttl_seconds,23)

    def test_storage_delay_rechecks_expiry(self):
        def delay(): self.now=10900
        self.signer.check=delay
        with self.assertRaises(Denied): self.issue()
        self.assertEqual(len(self.signer.calls),0)

    def test_storage_delay_rechecks_admin_mfa(self):
        with self.engine.begin() as c:
            c.execute(insert(memberships).values(tenant_id="tenant_a",subject="user_a",active=True))
        def delay(): self.now=10290
        self.signer.check=delay
        with self.assertRaises(Denied): self.issue("user_a")
        self.assertEqual(len(self.signer.calls),0)

    def test_audit_failure_and_storage_failure_return_no_url(self):
        with patch.object(self.service,'_event',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.issue()
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(events)),0)
        self.signer.fail=True
        with self.assertRaises(RuntimeError): self.issue()

    def test_per_grant_issuance_limit(self):
        for _ in range(10): self.issue()
        with self.assertRaises(Denied): self.issue()
        self.assertEqual(len(self.signer.calls),10)

    def test_boto_signer_pins_object_get_expiry_and_checks_metadata(self):
        _,decision=self.issue()
        signer=R2Signer('synthetic-key','synthetic-secret')
        with patch.object(signer.client,'head_object',return_value={'ContentLength':CLINIC_1_0_0.bytes,
                           'ETag':'"'+EXPECTED_ETAG+'"'}): signer.check()
        with patch.object(signer.client,'head_object',return_value={'ContentLength':1,'ETag':'wrong'}):
            with self.assertRaises(ValueError): signer.check()
        signed=signer.sign(decision)
        parsed=urlsplit(signed)
        params=parse_qs(parsed.query)
        self.assertEqual(parsed.netloc,urlsplit(R2_ENDPOINT).netloc)
        self.assertEqual(parsed.path,'/'+CLINIC_1_0_0.bucket+'/'+CLINIC_1_0_0.object_key)
        self.assertEqual(params['X-Amz-Expires'],['300'])
        self.assertEqual(params['X-Amz-Algorithm'],['AWS4-HMAC-SHA256'])
        self.assertNotIn('synthetic-secret',signed)

    def test_http_download_requires_csrf_and_returns_private_no_store_page(self):
        with self.engine.begin() as c:
            c.execute(update(sessions).where(sessions.c.subject=='user_customer').values(token_hash=digest('browser-token')))
        config=Config('https://gateway.example','client_synthetic','sk_synthetic',True,True,(),False,True,True)
        with TestClient(create_app(config,self.engine,clock=lambda:self.now,download_signer=self.signer),
                        base_url=config.origin,follow_redirects=False) as client:
            client.cookies.set(SESSION_COOKIE,'browser-token')
            data={'csrf':'synthetic','grant_id':'grant_test'}
            self.assertEqual(client.post('/api/downloads',data=data).status_code,403)
            response=client.post('/api/downloads',data=data,headers={'origin':config.origin})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(response.headers['referrer-policy'],'no-referrer')
            self.assertIn('Private installer download',response.text)

if __name__=='__main__': unittest.main()
