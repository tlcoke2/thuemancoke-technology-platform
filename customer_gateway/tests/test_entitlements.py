import os
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine, insert, select, update, func
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from customer_gateway.app import metadata as auth_metadata, sessions
from customer_gateway.entitlements import (metadata, tenants, memberships, admins,
    elevations, grants, events, Entitlements, Denied, RELEASE)


class EntitlementTests(unittest.TestCase):
    def setUp(self):
        url = os.environ.get('GATEWAY_TEST_POSTGRES_URL')
        if url:
            parsed = make_url(url)
            if parsed.host not in ('localhost', '127.0.0.1') or parsed.database != 'gateway_test':
                raise RuntimeError('Only isolated local gateway_test is allowed')
            self.engine = create_engine(url)
            metadata.drop_all(self.engine)
            auth_metadata.drop_all(self.engine)
        else:
            self.engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread':False})
        auth_metadata.create_all(self.engine)
        metadata.create_all(self.engine)
        self.now = 10000
        self.service = Entitlements(self.engine, sessions, lambda: self.now)
        with self.engine.begin() as c:
            c.execute(insert(tenants), [{'id':'tenant_a','active':True}, {'id':'tenant_b','active':False}])
            for subject in ('user_a', 'user_b', 'user_customer'):
                c.execute(insert(sessions).values(token_hash=subject, subject=subject, csrf='synthetic', expires=10900))
                c.execute(insert(elevations).values(session_hash=subject, subject=subject,
                    verified_at=9990, expires=10290, provider_reference='synthetic-test-only'))
            c.execute(insert(admins), [{'subject':'user_a','active':True}, {'subject':'user_b','active':True}])

    def tearDown(self):
        metadata.drop_all(self.engine)
        auth_metadata.drop_all(self.engine)
        self.engine.dispose()

    def propose(self, actor='user_a', **overrides):
        args = dict(tenant_id='tenant_a', release_id=RELEASE, starts=10000, expires=12000,
                    contract_reference='synthetic-contract', approval_reference='synthetic-review')
        args.update(overrides)
        return self.service.propose(actor, **args)

    def state(self, grant_id):
        with self.engine.connect() as c:
            return c.execute(select(grants).where(grants.c.id == grant_id)).mappings().one()['state']

    def test_two_person_approval_and_idempotent_revocation(self):
        g = self.propose()
        self.assertEqual(self.state(g), 'pending')
        self.service.approve('user_b', g)
        self.service.approve('user_b', g)
        self.assertEqual(self.state(g), 'approved')
        self.service.revoke('user_a', g)
        self.service.revoke('user_a', g)
        self.assertEqual(self.state(g), 'revoked')
        with self.assertRaises(Denied): self.service.approve('user_b', g)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(events)), 3)

    def test_self_approval_customer_and_forged_session_denied(self):
        g = self.propose()
        for actor in ('user_a', 'user_customer', 'forged'):
            with self.subTest(actor=actor), self.assertRaises(Denied):
                self.service.approve(actor, g)
        self.assertEqual(self.state(g), 'pending')

    def test_elevation_expiry_and_cross_session_binding(self):
        self.now = 10290
        with self.assertRaises(Denied): self.propose()
        self.now = 10000
        with self.engine.begin() as c:
            c.execute(update(elevations).where(elevations.c.session_hash == 'user_a').values(subject='user_b'))
        with self.assertRaises(Denied): self.propose()

    def test_disabled_admin_and_expired_session(self):
        with self.engine.begin() as c:
            c.execute(update(admins).where(admins.c.subject == 'user_a').values(active=False))
        with self.assertRaises(Denied): self.propose()
        self.now = 10900
        with self.assertRaises(Denied): self.propose('user_b')

    def test_invalid_contract_release_tenant_and_interval(self):
        for overrides in ({'contract_reference':''}, {'approval_reference':' '},
                          {'release_id':'arbitrary-object'}, {'tenant_id':'tenant_b'},
                          {'tenant_id':'unknown'}, {'expires':10000}, {'starts':True}):
            with self.subTest(overrides=overrides), self.assertRaises(Denied): self.propose(**overrides)

    def test_expired_proposal_and_disabled_proposer(self):
        g = self.propose(expires=10001)
        self.now = 10001
        with self.assertRaises(Denied): self.service.approve('user_b', g)
        self.now = 10000
        with self.engine.begin() as c:
            c.execute(update(admins).where(admins.c.subject == 'user_a').values(active=False))
        with self.assertRaises(Denied): self.service.approve('user_b', g)

    def test_audit_failure_rolls_back_approval_and_revocation(self):
        g = self.propose()
        with patch.object(self.service, '_event', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.service.approve('user_b', g)
        self.assertEqual(self.state(g), 'pending')
        self.service.approve('user_b', g)
        with patch.object(self.service, '_event', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError): self.service.revoke('user_a', g)
        self.assertEqual(self.state(g), 'approved')

    def test_no_membership_or_admin_created_by_proposal(self):
        self.propose()
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(memberships)), 0)
            self.assertEqual(c.scalar(select(func.count()).select_from(admins)), 2)

if __name__ == '__main__': unittest.main()
