"""Synthetic Railway CLI UAT provenance: no network, real accounts or release objects."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from customer_gateway.record_railway_provenance import attach, main, select_deployment
from customer_gateway.validate_revocation_evidence import TEMPLATE, evaluate, progress


def report():
    doc=copy.deepcopy(TEMPLATE)
    doc["git_commit"]=""
    doc["url_ttl_seconds"]=300
    doc["checks"]={key:True for key in TEMPLATE["checks"]}
    doc["timestamps_utc"]={
        "url_issued":"2026-11-04T16:24:00Z",
        "grant_revoked":"2026-11-04T16:25:00Z",
        "post_revoke_denial":"2026-11-04T16:25:05Z",
        "expired_r2_get_attempt":"2026-11-04T16:30:10Z",
    }
    doc["http_statuses"]={
        "before_approval_download":403,
        "self_approval":403,
        "approved_download":200,
        "other_tenant_download":403,
        "post_revoke_download":403,
        "expired_r2_get":403,
        "old_session_account":401,
        "new_session_revoked_download":403,
    }
    doc["audit_counts"]={
        "download_issued_before_revoke":1,
        "download_issued_after_revoke":1,
        "grant_revoke_events":1,
    }
    return doc


def listing():
    return [
        {"id":"b56fd4e9-4299-4bb8-857d-185099bf8141","status":"SUCCESS",
         "createdAt":"2026-11-04T15:57:02.500Z","meta":{}},
        {"id":"0fb03434-435e-4317-a55b-fb1ed49f9440","status":"REMOVED",
         "createdAt":"2026-11-04T12:27:09.187Z","meta":{}},
        {"id":"068311e8-bba9-4097-b96e-abf86fb7455b","status":"REMOVED",
         "createdAt":"2026-11-04T12:29:42.940Z","meta":{}},
    ]


class RailwayProvenanceTests(unittest.TestCase):
    def test_chooses_active_at_test_time_not_old_removed_deployment(self):
        doc=report()
        mode=attach(doc,listing())
        self.assertIn("Railway deployment UUID",mode)
        self.assertEqual(doc["railway_deployment_id"],"b56fd4e9-4299-4bb8-857d-185099bf8141")
        self.assertEqual(doc["railway_deployment_created_at"],"2026-11-04T15:57:02.500Z")
        self.assertEqual(doc["git_commit"],"")
        self.assertTrue(evaluate(doc)[0])
        self.assertIn("Railway deployment provenance: UUID + UTC createdAt recorded",progress(doc))

    def test_older_deployment_not_mistaken_for_latest(self):
        doc=report()
        doc["timestamps_utc"]["url_issued"]="2026-11-04T12:28:00Z"
        doc["timestamps_utc"]["grant_revoked"]="2026-11-04T12:28:10Z"
        doc["timestamps_utc"]["post_revoke_denial"]="2026-11-04T12:28:20Z"
        selected=select_deployment(doc,listing())
        self.assertEqual(selected["id"],"0fb03434-435e-4317-a55b-fb1ed49f9440")

    def test_refuses_deployment_issued_after_test(self):
        doc=report()
        values=listing()
        values[0]["createdAt"]="2026-11-04T16:24:02.000Z"
        with self.assertRaises(ValueError):
            select_deployment(doc,values)

    def test_refuses_in_test_redeployment(self):
        doc=report()
        vals=listing()
        vals.append({"id":"360ed0be-a38a-4b6a-9670-f5056ead9fdc",
                     "createdAt":"2026-11-04T16:24:30Z","status":"REMOVED"})
        with self.assertRaises(ValueError):
            select_deployment(doc,vals)

    def test_propagates_actual_valid_git_sha_when_available(self):
        doc=report()
        vals=listing()
        vals[0]["meta"]={"commitHash":"a"*40}
        method=attach(doc,vals)
        self.assertIn("Git commit",method)
        self.assertEqual(doc["git_commit"],"a"*40)
        self.assertNotIn("railway_deployment_id",doc)
        self.assertTrue(evaluate(doc)[0])

    def test_rejects_unknown_layout_ambiguous_status_and_duplicate(self):
        doc=report()
        for vals in ([{"id":"bad","createdAt":"2026-11-04T15:57:00Z","status":"SUCCESS"}],
                     listing()+listing(),
                     [{"id":listing()[0]["id"],"createdAt":"2026-11-04T15:57:02.500Z",
                       "status":"UNKNOWN"}]):
            with self.subTest(values=vals),self.assertRaises(ValueError):
                select_deployment(doc,vals)

    def test_cli_writes_new_copy_only_and_never_overwrites(self):
        with TemporaryDirectory() as folder:
            inp=Path(folder)/"evidence.json"
            cli=Path(folder)/"deployments.json"
            out=Path(folder)/"with-provenance.json"
            inp.write_text(json.dumps(report()),encoding="utf-8")
            cli.write_text(json.dumps(listing()),encoding="utf-8")
            before=inp.read_bytes()
            self.assertEqual(main(["--input",str(inp),"--railway-list",str(cli),"--output",str(out)]),0)
            self.assertEqual(inp.read_bytes(),before)
            self.assertTrue(evaluate(json.loads(out.read_text(encoding="utf-8")))[0])
            prior=out.read_bytes()
            self.assertEqual(main(["--input",str(inp),"--railway-list",str(cli),"--output",str(out)]),2)
            self.assertEqual(out.read_bytes(),prior)

    def test_wrong_git_commit_or_extra_fields_not_accepted(self):
        doc=report()
        doc["git_commit"]="b"*64
        with self.assertRaises(ValueError):
            attach(doc,listing())
        doc=report()
        doc["railway_deployment_id"]="x"
        with self.assertRaises(ValueError):
            attach(doc,listing())


if __name__=="__main__":
    unittest.main()
