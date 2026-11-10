"""Offline verifier regression tests: no R2, database, clinical data or signed URLs."""
import tempfile
import unittest
from pathlib import Path
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from customer_gateway.verify_downloaded_release import inspect_archive, main


class ReadbackVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'synthetic.tar.gz'
        self.data = b'controlled-synthetic-release-bytes'
        self.path.write_bytes(self.data)
        self.release = SimpleNamespace(
            id='synthetic-fixture',
            bytes=len(self.data),
            sha256=hashlib.sha256(self.data).hexdigest(),
        )

    def test_matching_local_bytes_pass_and_never_claim_signature_validation(self):
        report = inspect_archive(self.path, release=self.release)
        self.assertTrue(report['verified'])
        self.assertTrue(report['size_matches'])
        self.assertTrue(report['sha256_matches'])
        self.assertFalse(report['publisher_signature_verified'])
        self.assertEqual(report['observed_bytes'], len(self.data))
        self.assertNotIn(str(self.path.parent), str(report))

    def test_modified_bytes_same_size_are_rejected(self):
        self.path.write_bytes(b'X' + self.data[1:])
        report = inspect_archive(self.path, release=self.release)
        self.assertTrue(report['size_matches'])
        self.assertFalse(report['sha256_matches'])
        self.assertFalse(report['verified'])

    def test_truncated_download_is_rejected(self):
        self.path.write_bytes(self.data[:-1])
        report = inspect_archive(self.path, release=self.release)
        self.assertFalse(report['size_matches'])
        self.assertFalse(report['verified'])

    def test_missing_archive_and_url_are_rejected(self):
        with self.assertRaises(ValueError):
            inspect_archive(self.path.with_name('absent.tar.gz'), release=self.release)
        with self.assertRaises(ValueError):
            inspect_archive('https://example.invalid/signed?token=secret', release=self.release)

    def test_evidence_record_does_not_overwrite(self):
        evidence_path = Path(self.temp.name) / 'evidence.json'
        evidence_path.write_text('prior-evidence', encoding='utf-8')
        with patch('customer_gateway.verify_downloaded_release.CLINIC_1_0_0', self.release):
            self.assertEqual(main(['--file', str(self.path), '--evidence-json', str(evidence_path)]), 2)
        self.assertEqual(evidence_path.read_text(encoding='utf-8'), 'prior-evidence')

    def test_cli_exit_code_for_mismatch(self):
        with patch('customer_gateway.verify_downloaded_release.CLINIC_1_0_0', self.release):
            self.assertEqual(main(['--file', str(self.path)]), 0)
            self.path.write_bytes(b'changed')
            self.assertEqual(main(['--file', str(self.path)]), 1)


if __name__ == '__main__':
    unittest.main()
