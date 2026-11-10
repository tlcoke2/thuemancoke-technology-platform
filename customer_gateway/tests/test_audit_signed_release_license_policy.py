"""Synthetic, offline tests of signed-package licence-policy detector; no clinic or key data."""
import io
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from customer_gateway.audit_signed_release_license_policy import (
    MAX_POLICY_BYTES, POLICY_PATH, read_packaged_source, review_policy_source, main,
)
from customer_gateway.verify_release_manifest import VerificationError


OLD = """
if (process.env.LICENSE_DISABLE === '1') {
  res.setHeader('X-License-Bypass', 'env');
  return next();
}
if (req.user?.role === 'Admin') {
  res.setHeader('X-License-Bypass', 'admin');
  req.license = { modules: ['*'], adminBypass: true };
  return next();
}
"""
HARDENED = """
if (process.env.LICENSE_DISABLE === '1') {
  return res.status(503).json({ error: 'Unsafe licence configuration' });
}
if (req.user?.role === 'Superadmin') {
  res.setHeader('X-License-Bypass', 'superadmin');
  return next();
}
"""


def package(files, destination):
    with tarfile.open(destination, "w:gz") as archive:
        for name, data in files:
            blob = data.encode() if isinstance(data,str) else data
            item = tarfile.TarInfo(name)
            item.size = len(blob)
            archive.addfile(item, io.BytesIO(blob))


class CommercialPolicyInspectionTests(unittest.TestCase):
    def test_known_bypasses_detected(self):
        self.assertEqual(review_policy_source(OLD),{
            "admin_bypass_signature":True,
            "global_env_bypass_signature":True,
        })

    def test_source_fix_no_known_bypass_patterns(self):
        self.assertEqual(review_policy_source(HARDENED),{
            "admin_bypass_signature":False,
            "global_env_bypass_signature":False,
        })

    def test_tar_member_exact_or_wrapper(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"synthetic.tar.gz"
            for name in (POLICY_PATH, "TEC-EPR-SIGNED/"+POLICY_PATH):
                package([(name,OLD)],archive)
                self.assertEqual(read_packaged_source(archive),OLD)

    def test_absent_source_in_docker_bundle_is_inconclusive(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"synthetic.tar.gz"
            package([("images.tar",b"synthetic-test-not-a-real-image")],archive)
            self.assertIsNone(read_packaged_source(archive))

    def test_duplicate_paths_are_invalid(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"synthetic.tar.gz"
            package([(POLICY_PATH,OLD),("prefix/"+POLICY_PATH,HARDENED)],archive)
            with self.assertRaises(VerificationError):
                read_packaged_source(archive)

    def test_oversize_is_rejected(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"synthetic.tar.gz"
            package([(POLICY_PATH,b"a"*(MAX_POLICY_BYTES+1))],archive)
            with self.assertRaises(VerificationError):
                read_packaged_source(archive)

    def test_never_read_unverified_archive(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/"bad.tar.gz"
            path.write_bytes(b"garbage")
            with patch("customer_gateway.audit_signed_release_license_policy.verify_release_payload",
                       side_effect=VerificationError("signature mismatch")), patch(
                       "customer_gateway.audit_signed_release_license_policy.read_packaged_source") as read:
                self.assertEqual(main(["--release-dir",folder,"--public-key",str(path),
                                       "--archive",str(path)]),2)
                read.assert_not_called()

    def test_detection_blocks_commercial_result_even_with_mocked_integrity(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"synthetic.tar.gz"
            package([(POLICY_PATH,OLD)],archive)
            with patch("customer_gateway.audit_signed_release_license_policy.verify_release_payload",
                       return_value={"result":"PASS"}):
                self.assertEqual(main(["--release-dir",folder,"--public-key",str(archive),
                                       "--archive",str(archive)]),1)


if __name__ == "__main__":
    unittest.main()
