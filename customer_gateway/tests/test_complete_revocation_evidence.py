"""Synthetic offline guided UAT evidence completion regression tests."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import copy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from customer_gateway.complete_revocation_evidence import complete, main
from customer_gateway.validate_revocation_evidence import TEMPLATE, CHECKS


def _record():
    report=copy.deepcopy(TEMPLATE)
    report["http_statuses"]={
        "before_approval_download":"403",
        "self_approval":"403",
        "approved_download":"200",
        "other_tenant_download":"403",
        "post_revoke_download":"403",
        "expired_r2_get":"403",
        "old_session_account":"401",
        "new_session_revoked_download":"403",
    }
    report["audit_counts"]={
        "download_issued_before_revoke":"1",
        "download_issued_after_revoke":"1",
        "grant_revoke_events":"1",
    }
    report["url_ttl_seconds"]="300"
    base=datetime(2026,11,4,12,0,0,tzinfo=timezone.utc)
    report["timestamps_utc"]={
        "url_issued":base.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "grant_revoked":(base+timedelta(seconds=10)).isoformat(),
        "post_revoke_denial":(base+timedelta(seconds=11)).isoformat(),
        "expired_r2_get_attempt":(base+timedelta(seconds=335)).isoformat(),
    }
    return report


class GuidedEvidenceTests(unittest.TestCase):
    def test_each_pass_requires_explicit_operator_response(self):
        report=_record()
        answers=iter(["yes","no","","y"]+[""]*(len(CHECKS)-4)+[""])
        prompts=[]
        complete(report, ask=lambda question:(prompts.append(question) or next(answers)), say=lambda line:None)
        self.assertIs(report["checks"][CHECKS[0]],True)
        self.assertIs(report["checks"][CHECKS[1]],False)
        self.assertIsNone(report["checks"][CHECKS[2]])
        self.assertIs(report["checks"][CHECKS[3]],True)
        self.assertIsNone(report["checks"][CHECKS[4]])
        self.assertEqual(report["http_statuses"]["approved_download"],200)
        self.assertEqual(report["audit_counts"]["download_issued_before_revoke"],1)
        self.assertEqual(report["timestamps_utc"]["url_issued"],"2026-11-04T12:00:00Z")
        self.assertEqual(report["url_ttl_seconds"],300)
        self.assertEqual(report["git_commit"],"")
        self.assertTrue(any("MFA" in q for q in prompts))

    def test_incorrect_http_status_preserved(self):
        report=_record()
        report["http_statuses"]["post_revoke_download"]="200"
        answers=iter([""]*len(CHECKS)+[""])
        output=[]
        complete(report,ask=lambda _:next(answers),say=output.append)
        self.assertEqual(report["http_statuses"]["post_revoke_download"],200)
        self.assertTrue(any("post_revoke_download" in line for line in output))

    def test_unknown_naive_dates_not_converted(self):
        report=_record()
        report["timestamps_utc"]["url_issued"]="2026-11-04 12:00:00"
        answers=iter([""]*len(CHECKS)+["",""])
        messages=[]
        complete(report,ask=lambda _:next(answers),say=messages.append)
        self.assertEqual(report["timestamps_utc"]["url_issued"],"2026-11-04 12:00:00")
        self.assertTrue(any("MISSING/INVALID UTC timestamp" in line for line in messages))

    def test_declared_utc_time_and_actual_deployed_commit_can_be_supplied(self):
        report=_record()
        report["timestamps_utc"]["url_issued"]=None
        answers=iter([""]*len(CHECKS)+["2026-11-04T12:00:00Z","a"*40])
        complete(report,ask=lambda _:next(answers),say=lambda _:None)
        self.assertEqual(report["timestamps_utc"]["url_issued"],"2026-11-04T12:00:00Z")
        self.assertEqual(report["git_commit"],"a"*40)

    def test_original_untouched_and_exclusive_new_report(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/"original.json"
            reviewed=Path(temp)/"reviewed.json"
            path.write_text(json.dumps(_record()),encoding="utf-8")
            before=path.read_bytes()
            answers=iter([""]*len(CHECKS)+[""])
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(path),"--output",str(reviewed)],
                    ask=lambda _:next(answers)),1)
            self.assertEqual(path.read_bytes(),before)
            self.assertTrue(reviewed.exists())
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(path),"--output",str(reviewed)],
                    ask=lambda _:raise_unexpected()),2)
            self.assertEqual(path.read_bytes(),before)

    def test_same_path_refused(self):
        with TemporaryDirectory() as temp:
            source=Path(temp)/"original.json"
            source.write_text(json.dumps(_record()),encoding="utf-8")
            original=source.read_bytes()
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(source),"--output",str(source)],
                    ask=lambda _:raise_unexpected()),2)
            self.assertEqual(source.read_bytes(),original)


def raise_unexpected():
    raise AssertionError("No confirmation prompts should run after path check")


if __name__=="__main__":
    unittest.main()
