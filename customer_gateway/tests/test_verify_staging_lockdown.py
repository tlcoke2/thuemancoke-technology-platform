"""Synthetic local Railway staging switch audit, never touches a live service."""
from contextlib import redirect_stdout
from io import StringIO
import json
import subprocess
import unittest
from unittest.mock import Mock

from customer_gateway.verify_staging_lockdown import CLI, FLAGS, check, read_variables, main


class StagingLockdownTests(unittest.TestCase):
    def test_fixed_cli_cannot_target_production(self):
        self.assertEqual(CLI, ("railway", "variable", "list", "--service",
                                "tcl-customer-gateway-staging", "--environment",
                                "staging", "--json"))
        self.assertEqual(len(FLAGS), 2)

    def test_explicit_disabled_values_only(self):
        self.assertEqual(check({"GATEWAY_DOWNLOADS_ENABLED":"false",
                                "GATEWAY_RELEASE_APPROVED":"FALSE"}),
                         {flag:True for flag in FLAGS})
        self.assertEqual(check({"GATEWAY_DOWNLOADS_ENABLED":False,
                                "GATEWAY_RELEASE_APPROVED":False}),
                         {flag:True for flag in FLAGS})
        for unsafe in ("true", "0", "", None, True, 0, 1, "disabled", {}, []):
            with self.subTest(value=repr(unsafe)):
                values = {"GATEWAY_DOWNLOADS_ENABLED":unsafe,
                          "GATEWAY_RELEASE_APPROVED":"false"}
                self.assertFalse(check(values)["GATEWAY_DOWNLOADS_ENABLED"])

    def test_read_only_cli_load_never_echo_secrets(self):
        result=Mock(returncode=0, stdout=json.dumps({
            "GATEWAY_DOWNLOADS_ENABLED":"false",
            "GATEWAY_RELEASE_APPROVED":"false",
            "WORKOS_API_KEY":"sk_sensitive_placeholder",
        }))
        runner=Mock(return_value=result)
        values=read_variables(runner)
        self.assertEqual(values["GATEWAY_DOWNLOADS_ENABLED"],"false")
        self.assertEqual(runner.call_args.args[0],CLI)
        self.assertFalse(runner.call_args.kwargs.get("shell",False))
        log=StringIO()
        with redirect_stdout(log):
            self.assertEqual(main([], reader=lambda:values),0)
        self.assertNotIn("sk_sensitive",log.getvalue())
        self.assertIn("PASS:",log.getvalue())

    def test_missing_or_true_fails_and_never_logs_raw_values(self):
        values={"GATEWAY_DOWNLOADS_ENABLED":"true",
                "GATEWAY_RELEASE_APPROVED":"false",
                "DATABASE_URL":"postgresql://privatehost/secret"}
        log=StringIO()
        with redirect_stdout(log):
            self.assertEqual(main([], reader=lambda:values),1)
        self.assertNotIn("postgresql://",log.getvalue())
        self.assertIn("NOT VERIFIED DISABLED",log.getvalue())
        with redirect_stdout(StringIO()):
            self.assertEqual(main([], reader=lambda:{}),1)

    def test_network_or_json_error_is_redacted(self):
        for error in (TimeoutError("private secret"),ValueError("private secret"),
                      subprocess.SubprocessError("private secret")):
            with self.subTest(error=type(error)):
                log=StringIO()
                with redirect_stdout(log):
                    self.assertEqual(main([], reader=lambda:(_ for _ in ()).throw(error)),2)
                self.assertNotIn("private secret",log.getvalue())

    def test_windows_powershell_stdin_mode_verifies_without_echoing_secrets(self):
        variables={"GATEWAY_DOWNLOADS_ENABLED":"false",
                   "GATEWAY_RELEASE_APPROVED":"false",
                   "WORKOS_API_KEY":"sk_test_should_never_print",
                   "R2_SECRET_ACCESS_KEY":"test_private_value_should_never_print"}
        out=StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["--stdin"], reader=lambda: self.fail(
                "subprocess CLI should not be called in stdin mode"),
                stdin=StringIO(json.dumps(variables))),0)
        self.assertNotIn("should_never_print",out.getvalue())
        self.assertIn("GATEWAY_DOWNLOADS_ENABLED: DISABLED",out.getvalue())
        self.assertIn("GATEWAY_RELEASE_APPROVED: DISABLED",out.getvalue())

    def test_stdin_mode_rejects_bad_or_missing_or_secret_only_data(self):
        for raw in ("", "not-json", "[]", '{"GATEWAY_DOWNLOADS_ENABLED":"false"}',
                    '{"GATEWAY_DOWNLOADS_ENABLED":"true","GATEWAY_RELEASE_APPROVED":"false"}'):
            with self.subTest(raw=raw[:10]):
                out=StringIO()
                with redirect_stdout(out):
                    code=main(["--stdin"],stdin=StringIO(raw))
                self.assertNotEqual(code,0)
                self.assertNotIn("true",out.getvalue())
                self.assertNotIn("not-json",out.getvalue())

    def test_utf8_bom_stdin_accepted_and_empty_blocked(self):
        raw='\ufeff{"GATEWAY_DOWNLOADS_ENABLED":"false","GATEWAY_RELEASE_APPROVED":"false"}'
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["--stdin"],stdin=StringIO(raw)),0)
            self.assertEqual(main(["--stdin"],stdin=StringIO("")),2)

    def test_invalid_cli_result_rejected_without_values_echo(self):
        runner=Mock(return_value=Mock(returncode=0,stdout="[1,2,3]"))
        with self.assertRaises(ValueError):
            read_variables(runner)
        runner=Mock(return_value=Mock(returncode=1,stdout="secret response"))
        with self.assertRaises(ValueError):
            read_variables(runner)


if __name__ == "__main__":
    unittest.main()
