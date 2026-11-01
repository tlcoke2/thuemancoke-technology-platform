import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from commercial_core.download_policy import (
    CLINIC_1_0_0, Denied, Grant, Membership, Principal, Role, authorize_download,
)


class DownloadPolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
        self.p = Principal("https://identity.example", "user-a", True,
                           self.now + timedelta(hours=1), Role.CUSTOMER)
        self.m = Membership(self.p.issuer, self.p.subject, "tenant-a", True)
        self.g = Grant("grant-a", "tenant-a", CLINIC_1_0_0.id, "approved",
                       self.now - timedelta(days=1), self.now + timedelta(days=1),
                       "approval-a", "pilot-contract-a")
        self.args = dict(enabled=True, trusted_issuer=self.p.issuer,
                         principal=self.p, membership=self.m, grant=self.g,
                         requested_tenant="tenant-a", requested_release=CLINIC_1_0_0.id,
                         now=self.now, release_withdrawn=False)

    def call(self, **changes):
        return authorize_download(**dict(self.args, **changes))

    def test_valid_customer_gets_only_pinned_release(self):
        decision = self.call()
        self.assertEqual(decision.release, CLINIC_1_0_0)
        self.assertEqual(decision.ttl_seconds, 300)
        self.assertEqual(decision.expires_at, self.now + timedelta(seconds=300))

    def test_flags_fail_closed(self):
        for changes in ({"enabled": False}, {"enabled": "true"},
                        {"release_withdrawn": True}, {"release_withdrawn": None}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.call(**changes)
        args = dict(self.args)
        del args["release_withdrawn"]
        with self.assertRaises(Denied):
            authorize_download(**args)

    def test_untrusted_or_unverified_identity(self):
        for changes in ({"issuer": "https://attacker.example"}, {"subject": ""},
                        {"email_verified": False}, {"email_verified": "true"},
                        {"role": "owner-superadmin"}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.call(principal=replace(self.p, **changes))

    def test_cross_tenant_access_and_inactive_membership(self):
        for changes in ({"tenant_id": "tenant-b"}, {"subject": "user-b"},
                        {"issuer": "https://other.example"}, {"active": False}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.call(membership=replace(self.m, **changes))
        with self.assertRaises(Denied):
            self.call(requested_tenant="tenant-b")
        with self.assertRaises(Denied):
            self.call(grant=replace(self.g, tenant_id="tenant-b"))

    def test_admin_requires_mfa_and_has_no_tenant_bypass(self):
        admin = replace(self.p, role=Role.ADMIN)
        with self.assertRaises(Denied):
            self.call(principal=admin)
        admin = replace(admin, mfa_verified=True)
        self.assertEqual(self.call(principal=admin).ttl_seconds, 300)
        with self.assertRaises(Denied):
            self.call(principal=admin, requested_tenant="tenant-b")

    def test_pending_revoked_and_incomplete_grants(self):
        for changes in ({"state": "pending"}, {"state": "revoked"},
                        {"approval_reference": " "}, {"contract_reference": ""},
                        {"id": ""}, {"release_id": "unapproved-release"}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.call(grant=replace(self.g, **changes))

    def test_cannot_select_arbitrary_object(self):
        for value in ("../../secret", "https://attacker.example", "other-release"):
            with self.subTest(value=value), self.assertRaises(Denied):
                self.call(requested_release=value)

    def test_expired_future_and_naive_timestamps(self):
        for changes in ({"expires_at": self.now},
                        {"starts_at": self.now + timedelta(seconds=1)},
                        {"expires_at": self.now.replace(tzinfo=None)}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.call(grant=replace(self.g, **changes))
        with self.assertRaises(Denied):
            self.call(principal=replace(self.p, session_expires_at=self.now))
        with self.assertRaises(Denied):
            self.call(now=self.now.replace(tzinfo=None))

    def test_url_lifetime_never_exceeds_session_or_grant(self):
        for seconds in (1, 60, 299):
            for field in ("session", "grant"):
                changes = {"principal": replace(self.p, session_expires_at=self.now + timedelta(seconds=seconds))} if field == "session" else {"grant": replace(self.g, expires_at=self.now + timedelta(seconds=seconds))}
                with self.subTest(seconds=seconds, field=field):
                    self.assertEqual(self.call(**changes).ttl_seconds, seconds)
        with self.assertRaises(Denied):
            self.call(grant=replace(self.g, expires_at=self.now + timedelta(milliseconds=500)))


if __name__ == "__main__":
    unittest.main()
