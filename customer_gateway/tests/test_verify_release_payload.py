"""Synthetic end-to-end payload binding tests: no real release or private key."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from customer_gateway.verify_release_payload import (
    verify_release_payload, VerificationError, RELEASE_STATUS, _manifest_records
)


class PayloadBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.archive = self.dir / 'downloaded.tar.gz'
        self.public = self.dir / 'synthetic-public.pem'
        self.public.write_text('synthetic fixture: OpenSSL is mocked', encoding='utf-8')
        self.contents = {
            'backend/package.json': b'{"name":"synthetic"}\n',
            'frontend/index.html': b'<h1>synthetic customer release</h1>',
            'images.tar': b'synthetic-images-not-patient-data',
        }
        self.file_entries = {
            p: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
            for p,b in self.contents.items()
        }
        self.manifest = {
            'releaseVersion': '1.0.0', 'status': RELEASE_STATUS,
            'files': self.file_entries,
        }
        self.manifest_path = self.dir / 'manifest.json'
        self.manifest_path.write_text(json.dumps(self.manifest,sort_keys=True),encoding='utf-8')
        (self.dir/'manifest.sig').write_text('synthetic-no-secret',encoding='utf-8')
        (self.dir/'manifest.signer.json').write_text('{"synthetic":true}',encoding='utf-8')
        self.pinned_manifest_sha = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        self.members = list(self.contents.items())
        self.pack()

    def pack(self, *, prefix='', duplicate=None, extra=None, link=None):
        with tarfile.open(self.archive,mode='w:gz') as tar:
            for name, content in self.members:
                fullname = prefix + '/' + name if prefix else './' + name
                info = tarfile.TarInfo(fullname)
                info.size = len(content)
                tar.addfile(info,io.BytesIO(content))
            if duplicate is not None:
                info = tarfile.TarInfo(duplicate)
                info.size=1
                tar.addfile(info, io.BytesIO(b'x'))
            if extra is not None:
                info = tarfile.TarInfo(extra)
                info.size=1
                tar.addfile(info, io.BytesIO(b'x'))
            if link is not None:
                info = tarfile.TarInfo(link)
                info.type = tarfile.SYMTYPE
                info.linkname = 'backend/package.json'
                tar.addfile(info)

    def sign_and_check(self, *, prefix='', archive_sha=None, archive_size=None):
        raw=self.archive.read_bytes()
        r=SimpleNamespace(
            id='synthetic-fixture',
            sha256=archive_sha or hashlib.sha256(raw).hexdigest(),
            bytes=archive_size if archive_size is not None else len(raw),
        )
        with patch('customer_gateway.verify_release_payload.verify_manifest',
                   return_value={'manifest_sha256':self.pinned_manifest_sha,
                                 'publisher_spki_sha256':'e'*64}) as verify:
            result=verify_release_payload(
                self.dir,self.public,self.archive,archive_prefix=prefix,
                expected_manifest_sha=self.pinned_manifest_sha,release=r,
                expected_fingerprint='e'*64,expected_sig_bytes=256)
            verify.assert_called_once()
            return result

    def test_all_members_match_a_signed_manifest(self):
        result=self.sign_and_check()
        self.assertEqual(result['manifest_files_verified'],len(self.contents))
        self.assertEqual(result['archive_sha256'],hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertTrue(result['all_declared_payload_files_matched'])

    def test_top_directory_prefix_must_be_explicit(self):
        self.pack(prefix='outer-folder')
        with self.assertRaises(VerificationError):
            self.sign_and_check()
        self.assertEqual(self.sign_and_check(prefix='outer-folder')['manifest_files_verified'],3)

    def test_changed_member_with_new_outer_digest_is_rejected(self):
        self.members[0] = ('backend/package.json',b'same-length-changed')
        self.pack()
        with self.assertRaisesRegex(VerificationError,'member size differs'):
            self.sign_and_check()

    def test_changed_member_same_length_rejected_even_with_new_outer_digest(self):
        name,before=self.members[0]
        self.members[0]=(name,bytes([before[0]^1])+before[1:])
        self.pack()
        with self.assertRaisesRegex(VerificationError,'content differs'):
            self.sign_and_check()

    def test_missing_member_rejected(self):
        self.members.pop()
        self.pack()
        with self.assertRaisesRegex(VerificationError,'missing one or more'):
            self.sign_and_check()

    def test_duplicate_and_unexpected_members_rejected(self):
        self.pack(duplicate='./backend/package.json')
        with self.assertRaisesRegex(VerificationError,'Duplicate file path'):
            self.sign_and_check()
        self.pack(extra='./secret-unsigned-config')
        with self.assertRaisesRegex(VerificationError,'Unexpected unsigned file'):
            self.sign_and_check()

    def test_symlink_and_traversal_rejected(self):
        self.pack(link='./untrusted')
        with self.assertRaisesRegex(VerificationError,'link or unsupported'):
            self.sign_and_check()
        self.pack(extra='../traversal')
        with self.assertRaisesRegex(VerificationError,'Unsafe'):
            self.sign_and_check()

    def test_pinned_outer_sha_required(self):
        with self.assertRaisesRegex(VerificationError,'Downloaded archive differs'):
            self.sign_and_check(archive_sha='0'*64)
        with self.assertRaisesRegex(VerificationError,'Downloaded archive differs'):
            self.sign_and_check(archive_size=1)

    def test_incorrect_or_duplicate_signed_manifest_rejected(self):
        with self.assertRaisesRegex(VerificationError,'pinned release manifest'):
            _manifest_records(self.manifest_path,'0'*64)
        self.manifest_path.write_text('{"releaseVersion":"1.0.0","releaseVersion":"1.0.0"}',encoding='utf-8')
        signed_hash=hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(VerificationError,'Duplicate JSON member'):
            _manifest_records(self.manifest_path,signed_hash)

    def test_untrusted_signature_prevents_archive_comparison(self):
        with patch('customer_gateway.verify_release_payload.verify_manifest',
                   side_effect=VerificationError('signature invalid')):
            with self.assertRaisesRegex(VerificationError,'signature invalid'):
                verify_release_payload(self.dir,self.public,self.archive,
                                       expected_manifest_sha=self.pinned_manifest_sha)

    def test_optional_bundled_signature_bytes_must_match_exactly(self):
        self.members.append(('manifest.json', self.manifest_path.read_bytes()))
        self.pack()
        result=self.sign_and_check()
        self.assertEqual(result['bundled_signing_metadata_files_verified'],1)
        self.members[-1]=('manifest.json',b'tampered manifest inside bundle')
        self.pack()
        with self.assertRaises(VerificationError):
            self.sign_and_check()


if __name__=='__main__':
    unittest.main()
