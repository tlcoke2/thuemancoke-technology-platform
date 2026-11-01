import unittest
from unittest.mock import patch
from sqlalchemy import insert, delete, select, func, event
from customer_gateway.tests import test_entitlements as fixtures
from customer_gateway.app import audit
from customer_gateway.entitlements import admins
from customer_gateway.appoint_admins import appoint, AppointmentError, lookup_user


class AppointmentTests(unittest.TestCase):
    def setUp(self):
        fixtures.EntitlementTests.setUp(self)
        with self.engine.begin() as c:
            c.execute(delete(admins))
            for subject in ('user_a','user_b'):
                c.execute(insert(audit).values(id=subject, subject=subject,
                    event='staging_mfa_verified', created=9999))
        self.users = {s:{'id':s,'email_verified':True,'email':s+'@example.com'} for s in ('user_a','user_b')}

    tearDown = fixtures.EntitlementTests.tearDown

    def run_appointment(self, **kwargs):
        args = dict(owner_id='user_a', approver_id='user_b', approver_email='user_b@example.com',
                    lookup=lambda s:self.users[s], now=10000)
        args.update(kwargs)
        return appoint(self.engine, **args)

    def count_admins(self):
        with self.engine.connect() as c: return c.scalar(select(func.count()).select_from(admins))

    def test_two_verified_users_are_appointed_once(self):
        self.assertTrue(self.run_appointment())
        self.assertFalse(self.run_appointment())
        self.assertEqual(self.count_admins(), 2)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(audit)), 4)

    def test_email_mismatch_unverified_and_duplicate_identity_refused(self):
        with self.assertRaises(AppointmentError): self.run_appointment(approver_email='other@example.com')
        with self.assertRaises(AppointmentError): self.run_appointment(approver_id='user_a')
        self.users['user_b']['email_verified'] = False
        with self.assertRaises(AppointmentError): self.run_appointment()
        self.assertEqual(self.count_admins(), 0)

    def test_missing_mfa_proof_refused(self):
        with self.engine.begin() as c: c.execute(delete(audit).where(audit.c.subject == 'user_b'))
        with self.assertRaises(AppointmentError): self.run_appointment()
        self.assertEqual(self.count_admins(), 0)

    def test_existing_partial_or_disabled_appointments_are_not_overwritten(self):
        with self.engine.begin() as c: c.execute(insert(admins).values(subject='user_a',active=False))
        with self.assertRaises(AppointmentError): self.run_appointment()
        with self.engine.connect() as c: self.assertFalse(c.scalar(select(admins.c.active)))

    def test_provider_failure_is_redacted_and_roles_not_written(self):
        def failure(subject): raise RuntimeError('secret-provider-response')
        with self.assertRaisesRegex(AppointmentError, 'Provider identity check failed') as error:
            self.run_appointment(lookup=failure)
        self.assertNotIn('secret-provider-response', str(error.exception))
        self.assertEqual(self.count_admins(), 0)

    def test_audit_failure_rolls_back_both_appointments(self):
        def fail(c, cursor, statement, parameters, context, executemany):
            if statement.startswith('INSERT INTO gateway_auth_audit'):
                raise RuntimeError('synthetic audit failure')
        event.listen(self.engine, 'before_cursor_execute', fail)
        try:
            with self.assertRaises(RuntimeError): self.run_appointment()
        finally:
            event.remove(self.engine, 'before_cursor_execute', fail)
        self.assertEqual(self.count_admins(), 0)

    def test_provider_identity_lookup_is_pinned_and_read_only(self):
        with patch('customer_gateway.appoint_admins.httpx.Client') as factory:
            client = factory.return_value.__enter__.return_value
            lookup_user('sk_synthetic','user_Test')
            factory.assert_called_once_with(timeout=10, follow_redirects=False)
            self.assertEqual(client.get.call_args.args[0], 'https://api.workos.com/user_management/users/user_Test')
            client.get.return_value.raise_for_status.assert_called_once()

if __name__ == '__main__': unittest.main()
