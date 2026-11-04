"""Synthetic safe Gate B report tests; never contact WorkOS, Railway or R2."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from customer_gateway.validate_revocation_evidence import TEMPLATE, evaluate, main, progress


class RevocationEvidenceTests(unittest.TestCase):
    def valid(self):
        data=copy.deepcopy(TEMPLATE)
        data['git_commit']='a'*40
        data['test_reference']='SYNTHETIC-UAT-REPORT'
        base=datetime(2026,11,4,12,0,0,tzinfo=timezone.utc)
        data['url_ttl_seconds']=300
        data['timestamps_utc']={
            'url_issued':base.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'grant_revoked':(base+timedelta(seconds=15)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'post_revoke_denial':(base+timedelta(seconds=16)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expired_r2_get_attempt':(base+timedelta(seconds=335)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        data['http_statuses']={
            'before_approval_download':403,
            'self_approval':403,
            'approved_download':200,
            'other_tenant_download':403,
            'post_revoke_download':403,
            'expired_r2_get':403,
            'old_session_account':401,
            'new_session_revoked_download':403,
        }
        data['audit_counts']={
            'download_issued_before_revoke':1,
            'download_issued_after_revoke':1,
            'grant_revoke_events':1,
        }
        data['checks']={key:True for key in data['checks']}
        return data

    def test_valid_attested_report_is_not_claimed_live_in_validator(self):
        passed,reasons=evaluate(self.valid())
        self.assertTrue(passed, reasons)

    def test_blank_template_is_pending(self):
        passed,reasons=evaluate(copy.deepcopy(TEMPLATE))
        self.assertFalse(passed)
        self.assertTrue(reasons)

    def test_denied_new_link_required(self):
        report=self.valid()
        report['http_statuses']['post_revoke_download']=200
        self.assertFalse(evaluate(report)[0])

    def test_distinct_approver_and_tenant_required(self):
        for flag in ('separate_mfa_approver','cross_tenant_customer_denied'):
            report=self.valid()
            report['checks'][flag]=False
            self.assertFalse(evaluate(report)[0])

    def test_no_new_issuance_count(self):
        report=self.valid()
        report['audit_counts']['download_issued_after_revoke']=2
        self.assertFalse(evaluate(report)[0])

    def test_url_expiry_must_be_checked_after_ttl(self):
        report=self.valid()
        report['timestamps_utc']['expired_r2_get_attempt']='2026-11-04T12:04:00Z'
        self.assertFalse(evaluate(report)[0])

    def test_revocation_must_follow_issuance(self):
        report=self.valid()
        report['timestamps_utc']['grant_revoked']='2026-11-04T11:59:00Z'
        self.assertFalse(evaluate(report)[0])

    def test_sensitive_fields_and_values_rejected(self):
        for key, value in (
            ('signed_url','https://private.example.net/?X-Amz-Signature=x'),
            ('customer_email','synthetic@example.com'),
            ('authentication_cookie','secret'),
        ):
            report=self.valid()
            report[key]=value
            self.assertFalse(evaluate(report)[0])
        report=self.valid()
        report['test_reference']='https://private.example.net/path'
        self.assertFalse(evaluate(report)[0])

    def test_numeric_boolean_is_not_http_status(self):
        report=self.valid()
        report['http_statuses']['other_tenant_download']=True
        self.assertFalse(evaluate(report)[0])

    def test_rejects_loosened_environment_or_service(self):
        for key,value in [('environment','production'),('service','tec-epr-clinical')]:
            report=self.valid()
            report[key]=value
            self.assertFalse(evaluate(report)[0])

    def test_progress_lists_missing_field_names_only(self):
        report=copy.deepcopy(TEMPLATE)
        output=progress(report)
        self.assertIn("http_statuses: 0/8 recorded", output)
        self.assertIn("  - PENDING: checks.post_revoke_new_url_denied", output)
        self.assertTrue(any("PENDING/FAIL" in line for line in output))
        self.assertNotIn("https://", "\\n".join(output))
        complete=progress(self.valid())
        self.assertIn("Final validator: PASS (report consistency only)", complete)

    def test_progress_cli_reads_existing_without_writing(self):
        with TemporaryDirectory() as temp:
            evidence=Path(temp)/'evidence.json'
            evidence.write_text(json.dumps(TEMPLATE),encoding='utf-8')
            before=evidence.read_bytes()
            self.assertEqual(main(['--progress',str(evidence)]),1)
            self.assertEqual(evidence.read_bytes(),before)
            evidence.write_text(json.dumps(self.valid()),encoding='utf-8')
            self.assertEqual(main(['--progress',str(evidence)]),0)

    def test_file_mode_and_exclusive_template(self):
        with TemporaryDirectory() as temp:
            evidence=Path(temp)/'evidence.json'
            self.assertEqual(main(['--template',str(evidence)]),0)
            self.assertEqual(main(['--template',str(evidence)]),2)
            self.assertEqual(main(['--file',str(evidence)]),1)
            evidence.write_text(json.dumps(self.valid()),encoding='utf-8')
            self.assertEqual(main(['--file',str(evidence)]),0)


if __name__=='__main__':
    unittest.main()
