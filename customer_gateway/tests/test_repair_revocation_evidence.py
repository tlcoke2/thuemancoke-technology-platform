"""Synthetic tests for safe repair of redacted operator evidence only."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from customer_gateway.repair_revocation_evidence import (
    explicit_utc, repair, main, HTTP_EXPECTED,
)
from customer_gateway.validate_revocation_evidence import TEMPLATE, evaluate


def incomplete_record():
    report=copy.deepcopy(TEMPLATE)
    report["checks"]={key:True for key in TEMPLATE["checks"]}
    report["timestamps_utc"]={
        "url_issued":"2026-11-04",
        "grant_revoked":"2026-11-04 11:24:360",
        "post_revoke_denial":"2026-11-0412:28:20",
        "expired_r2_get_attempt":"2026-11-04 12:35:51",
    }
    report["http_statuses"]={key:"HTTP "+str(value) for key,value in HTTP_EXPECTED.items()}
    report["git_commit"]=""
    report["audit_counts"]={
        "download_issued_before_revoke":1,
        "download_issued_after_revoke":1,
        "grant_revoke_events":1,
    }
    report["url_ttl_seconds"]=300
    return report


class RepairEvidenceTests(unittest.TestCase):
    def test_explicit_time_offset_converts_only_with_user_supplied_zone(self):
        self.assertEqual(explicit_utc("2026-11-04T11:24:36-05:00"),
                         "2026-11-04T16:24:36Z")
        self.assertEqual(explicit_utc("2026-11-04T16:24:36Z"),
                         "2026-11-04T16:24:36Z")
        for value in ("2026-11-04","2026-11-04T11:24:36",
                      "2026-11-04 11:24:36","2026-11-04T11:24:360-05:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                explicit_utc(value)

    def test_correctly_observed_input_can_pass_without_mutating_flags(self):
        record=incomplete_record()
        original_checks=copy.deepcopy(record["checks"])
        entered_times=[
            "2026-11-04T11:20:00-05:00",
            "2026-11-04T11:24:36-05:00",
            "2026-11-04T12:28:20-05:00",
            "2026-11-04T12:35:51-05:00",
        ]
        answers=iter(entered_times+[str(v) for v in HTTP_EXPECTED.values()]+["a"*40])
        notes=[]
        repair(record, ask=lambda question:next(answers), say=notes.append)
        passed,issues=evaluate(record)
        self.assertTrue(passed,issues)
        self.assertEqual(record["checks"],original_checks)
        self.assertEqual(record["timestamps_utc"]["grant_revoked"],"2026-11-04T16:24:36Z")
        self.assertEqual(record["git_commit"],"a"*40)

    def test_blank_and_discrepant_answer_never_invent_expected_status(self):
        record=incomplete_record()
        answers=iter([""]*4+["200"]+[""]*7+[""])
        repair(record,ask=lambda _:next(answers),say=lambda _:None)
        self.assertEqual(record["http_statuses"]["before_approval_download"],200)
        self.assertEqual(record["http_statuses"]["post_revoke_download"],"HTTP 403")
        self.assertFalse(evaluate(record)[0])

    def test_existing_numeric_statuses_require_no_extra_prompts(self):
        record=incomplete_record()
        record["http_statuses"]={k:str(v) for k,v in HTTP_EXPECTED.items()}
        answers=iter([""]*4+[""])
        repair(record,ask=lambda _:next(answers),say=lambda _:None)
        self.assertEqual(record["http_statuses"],HTTP_EXPECTED)

    def test_do_not_accept_file_digest_as_deployed_commit(self):
        record=incomplete_record()
        answers=iter([""]*4+[""]*8+["f"*64])
        messages=[]
        repair(record,ask=lambda _:next(answers),say=messages.append)
        self.assertEqual(record["git_commit"],"")
        self.assertTrue(any("NOT a Git commit" in m for m in messages))

    def test_never_overwrite_source_or_existing_output(self):
        with TemporaryDirectory() as td:
            src=Path(td)/"source.json"
            target=Path(td)/"updated.json"
            src.write_text(json.dumps(incomplete_record()),encoding="utf-8")
            before=src.read_bytes()
            answers=iter([""]*4+[""]*8+[""])
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(src),"--output",str(target)],
                                      ask=lambda _:next(answers)),1)
            self.assertEqual(src.read_bytes(),before)
            target_before=target.read_bytes()
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(src),"--output",str(target)],
                                      ask=lambda _:self.fail("Must refuse existing output before prompting")),2)
            self.assertEqual(src.read_bytes(),before)
            self.assertEqual(target.read_bytes(),target_before)

    def test_reject_same_path_before_writes(self):
        with TemporaryDirectory() as td:
            src=Path(td)/"existing.json"
            src.write_text(json.dumps(incomplete_record()),encoding="utf-8")
            before=src.read_bytes()
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["--input",str(src),"--output",str(src)],
                                      ask=lambda _:self.fail("Must not prompt for same path")),2)
            self.assertEqual(src.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
