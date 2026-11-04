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
            self.assertEqual(main(reader=lambda:values),0)
        self.assertNotIn("sk_sensitive",log.getvalue())
        self.assertIn("PASS:",log.getvalue())

    def test_missing_or_true_fails_and_never_logs_raw_values(self):
        values={"GATEWAY_DOWNLOADS_ENABLED":"true",
                "GATEWAY_RELEASE_APPROVED":"false",
                "DATABASE_URL":"postgresql://privatehost/secret"}
        log=StringIO()
        with redirect_stdout(log):
            self.assertEqual(main(reader=lambda:values),1)
        self.assertNotIn("postgresql://",log.getvalue())
        self.assertIn("NOT VERIFIED DISABLED",log.getvalue())
        with redirect_stdout(StringIO()):
            self.assertEqual(main(reader=lambda:{}),1)

    def test_network_or_json_error_is_redacted(self):
        for error in (TimeoutError("private secret"),ValueError("private secret"),
                      subprocess.SubprocessError("private secret")):
            with self.subTest(error=type(error)):
                log=StringIO()
                with redirect_stdout(log):
                    self.assertEqual(main(reader=lambda:(_ for _ in ()).throw(error)),2)
                self.assertNotIn("private secret",log.getvalue())

    def test_invalid_cli_result_rejected_without_values_echo(self):
        runner=Mock(return_value=Mock(returncode=0,stdout="[1,2,3]"))
        with self.assertRaises(ValueError):
            read_variables(runner)
        runner=Mock(return_value=Mock(returncode=1,stdout="secret response"))
        with self.assertRaises(ValueError):
            read_variables(runner)


if __name__ == "__main__":
    unittest.main()
