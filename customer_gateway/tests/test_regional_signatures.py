import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import replace
from customer_gateway.downloads import R2Signer, SIGNATURE_HASHES, R2_ENDPOINT
from customer_gateway.download_policy import LICENCE_1_0_1

class SignatureReleaseTests(unittest.TestCase):
    def signer(self, sha):
        s=object.__new__(R2Signer)
        s.release=replace(LICENCE_1_0_1, sha256=sha)
        s.client=SimpleNamespace(
            get_object=lambda **kw: {'ContentLength':512,'Body':io.BytesIO(b'x'*512)},
            generate_presigned_url=lambda *args,**kw: R2_ENDPOINT+'/'+s.release.bucket+'/'+s.release.object_key+'.publisher.sig')
        return s
    def test_both_pinned_signatures_can_be_issued_after_exact_hash_check(self):
        for sha,signature in SIGNATURE_HASHES.items():
            s=self.signer(sha)
            with patch('customer_gateway.downloads.hashlib.sha256') as h:
                h.return_value.hexdigest.return_value=signature
                self.assertTrue(s.sign_signature(SimpleNamespace(release=s.release,ttl_seconds=300)).startswith('https://'))
    def test_wrong_signature_hash_and_unknown_archive_are_denied(self):
        for sha in list(SIGNATURE_HASHES)+['a'*64]:
            s=self.signer(sha)
            with self.assertRaises(ValueError):
                s.sign_signature(SimpleNamespace(release=s.release,ttl_seconds=300))
    def test_signature_cannot_outlive_download_policy(self):
        s=self.signer(next(iter(SIGNATURE_HASHES)))
        for ttl in (0,301):
            with self.assertRaises(ValueError):
                s.sign_signature(SimpleNamespace(release=s.release,ttl_seconds=ttl))
