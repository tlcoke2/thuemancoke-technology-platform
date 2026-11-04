"""Synthetic detached-manifest tests. No real private signing material or clinical release."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from customer_gateway.verify_release_manifest import verify_manifest, VerificationError


@unittest.skipUnless(shutil.which('openssl'), 'OpenSSL is required for offline signature verification')
class SignatureVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.key = self.root / 'test-only-private.pem'
        self.public = self.root / 'public.pem'
        self.sig = self.root / 'manifest.sig'
        self.manifest = self.root / 'manifest.json'
        # Fresh synthetic RSA-2048 key for tests; no signing key is ever committed.
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048',
                        '-out',str(self.key)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['openssl','pkey','-in',str(self.key),'-pubout','-out',str(self.public)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        spki = subprocess.run(['openssl','pkey','-pubin','-in',str(self.public),'-pubout',
            '-outform','DER'],check=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout
        self.fingerprint=hashlib.sha256(spki).hexdigest()
        (self.root/'manifest.signer.json').write_text(json.dumps({
            'kind':'TEC EPR clinical distribution release manifest',
            'algorithm':'RSA-SHA256','releaseVersion':'1.0.0',
            'publicKeySpkiSha256':self.fingerprint
        }),encoding='utf-8')
        self.manifest.write_bytes(b'{"synthetic":true,"data":"testing only"}\n')
        sig = self.root/'temp.bin'
        subprocess.run(['openssl','dgst','-sha256','-sign',str(self.key),
                        '-out',str(sig),str(self.manifest)],check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.sig.write_bytes(base64.b64encode(sig.read_bytes())+b'\n')

    def verify(self):
        return verify_manifest(self.root,self.public,expected_fingerprint=self.fingerprint,
                               expected_sig_bytes=256)

    def test_valid_synthetic_manifest_signature_and_spki(self):
        result=self.verify()
        self.assertEqual(result['result'],'PASS')
        self.assertFalse(result['archive_manifest_binding_checked'])
        self.assertEqual(result['manifest_sha256'],hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_tampered_manifest_fails(self):
        self.manifest.write_bytes(self.manifest.read_bytes()+b'\n')
        with self.assertRaises(VerificationError): self.verify()

    def test_signature_tamper_fails(self):
        data=bytearray(base64.b64decode(self.sig.read_bytes()))
        data[0]^=1
        self.sig.write_bytes(base64.b64encode(data)+b'\n')
        with self.assertRaises(VerificationError): self.verify()

    def test_mismatched_key_fingerprint_fails(self):
        other_key = self.root / 'unrelated-private.pem'
        subprocess.run(['openssl','genpkey','-algorithm','RSA',
            '-pkeyopt','rsa_keygen_bits:2048','-out',str(other_key)],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(['openssl','pkey','-in',str(other_key),'-pubout',
            '-out',str(self.public)],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        with self.assertRaisesRegex(VerificationError,'PUBLIC KEY MISMATCH'):
            self.verify()

    def test_unexpected_algorithm_or_version_fails(self):
        signer=self.root/'manifest.signer.json'
        original=signer.read_text(encoding='utf-8')
        for change in ('"RSA-PSS"', '"ECDSA"'):
            signer.write_text(original.replace('"RSA-SHA256"',change),encoding='utf-8')
            with self.assertRaises(VerificationError): self.verify()
        signer.write_text(original.replace('"1.0.0"','"2.0.0"'),encoding='utf-8')
        with self.assertRaises(VerificationError): self.verify()

    def test_missing_and_invalid_base64_fails(self):
        self.sig.write_text('not@base64',encoding='utf-8')
        with self.assertRaises(VerificationError): self.verify()
        self.sig.unlink()
        with self.assertRaises(VerificationError): self.verify()


if __name__=='__main__':
    unittest.main()
