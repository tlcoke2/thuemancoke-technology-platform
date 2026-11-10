"""Synthetic-only RSA-signed 1.0.1 archive integration. No real publisher key."""
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from customer_gateway.verify_release_101 import review_new_release, VerificationError
from customer_gateway.download_policy import CLINIC_1_0_0


class Clinical101ReleaseTests(unittest.TestCase):
    def setUp(self):
        if shutil.which('openssl') is None:
            self.skipTest('Only developer CI image without a local OpenSSL is unsupported')
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.public=self.root/'synthetic-public.pem'
        self.private=self.root/'synthetic-private.pem'
        self.signature=self.root/'raw.sig'
        self.archive=self.root/'TEC-EPR-Clinic-Edition-1.0.1-synthetic.tar.gz'
        self.evidence_path=self.root/'evidence.json'
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048',
                        '-out',str(self.private)],stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,check=True)
        subprocess.run(['openssl','pkey','-in',str(self.private),'-pubout',
                        '-out',str(self.public)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        der=subprocess.run(['openssl','pkey','-pubin','-in',str(self.public),
                            '-pubout','-outform','DER'],check=True,capture_output=True).stdout
        self.trusted=hashlib.sha256(der).hexdigest()
        self.contents={
            'backend/package.json':b'{"name":"synthetic-not-a-commercial-software-package"}',
            'backend/src/middleware/checkLicense.js':b'// synthetic signed customer enforcement only',
            'frontend/index.html':b'<html>SYNTHETIC NO PATIENT</html>',
            'images.tar':b'SYNTHETIC OCI IMAGES ONLY NOT REAL INSTALLERS',
            'compose.images.yaml':b'services:\n  backend:\n    pull_policy: never\n',
        }
        self.backend='a'*40
        self.frontend='b'*40
        self.refs={name:'SYNTHETIC-CI-ONLY-'+name for name in (
            'medicalDirector','security','existingCustomerUpgrade','offHostDR','publisher','gateway')}
        self.manifest={
            'format':1,'status':'APPROVED CLINICAL RELEASE 1.0.1',
            'releaseVersion':'1.0.1','targetReleaseVersion':'1.0.1',
            'candidateManifestSha256':'c'*64,'approvalEvidenceSha256':'d'*64,
            'scanEvidenceSha256':'e'*64,
            'reviewedImageIds':{
                'backend':'sha256:'+'1'*64,'frontend':'sha256:'+'2'*64,
                'database':'sha256:'+'3'*64},
            'source':{'backendRevision':self.backend,'frontendRevision':self.frontend},
            'approvalReferences':self.refs,'offline':{'createdAt':'2026-11-10T00:00:00.000Z'},
            'files':{key:{'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob)}
                     for key,blob in self.contents.items()},
        }
        self.prepare()

    def prepare(self):
        raw=json.dumps(self.manifest,sort_keys=True).encode()
        (self.root/'manifest.json').write_bytes(raw)
        subprocess.run(['openssl','dgst','-sha256','-sign',str(self.private),
                        '-out',str(self.signature),str(self.root/'manifest.json')],
                       capture_output=True,check=True)
        signer={'kind':'TEC EPR clinical distribution release manifest',
                'algorithm':'RSA-SHA256','releaseVersion':'1.0.1',
                'publicKeySpkiSha256':self.trusted}
        (self.root/'manifest.sig').write_text(
            base64.b64encode(self.signature.read_bytes()).decode()+'\n',encoding='utf8')
        (self.root/'manifest.signer.json').write_text(json.dumps(signer),encoding='utf8')
        with tarfile.open(self.archive,'w:gz') as t:
            for name,data in {**self.contents,
                    'manifest.json':raw,
                    'manifest.sig':(self.root/'manifest.sig').read_bytes(),
                    'manifest.signer.json':(self.root/'manifest.signer.json').read_bytes()}.items():
                item=tarfile.TarInfo('./'+name)
                item.size=len(data)
                t.addfile(item,io.BytesIO(data))
        archive_data=self.archive.read_bytes()
        self.evidence={
            'status':'SIGNED_PENDING_COMMERCIAL_GATEWAY_APPROVAL',
            'releaseVersion':'1.0.1','gatewayActivated':False,
            'publisherSpkiSha256':self.trusted,
            'archiveSha256':hashlib.sha256(archive_data).hexdigest(),
            'archiveBytes':len(archive_data)+10001,  # set below
            'archiveFilename':self.archive.name,
            'signedManifestSha256':hashlib.sha256(raw).hexdigest(),
            'approvalEvidenceSha256':'d'*64,
            'scanEvidenceSha256':'e'*64,
            'imageIds':self.manifest['reviewedImageIds'],
            'source':self.manifest['source'],
        }
        # The standard test fixture is compressible and may be under 10KB.
        # Add inert random bytes as a legitimate manifest-declared member.
        if len(archive_data)<10000:
            import os
            self.contents['images.tar']=os.urandom(24576)
            self.manifest['files']['images.tar']={
                'sha256':hashlib.sha256(self.contents['images.tar']).hexdigest(),
                'bytes':len(self.contents['images.tar'])}
            return self.prepare()
        self.evidence['archiveBytes']=len(archive_data)
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf8')

    def verify(self):
        return review_new_release(self.root,self.public,self.archive,self.evidence_path,
                                  expected_fingerprint=self.trusted,expected_sig_bytes=256)

    def test_full_101_RSA_signed_archive_and_every_member_authenticated(self):
        result=self.verify()
        self.assertEqual(result['assessment'],'VERIFIED_1_0_1_ARCHIVE_PENDING_HUMAN_GATEWAY_APPROVAL')
        self.assertTrue(result['publisherSignatureVerified'])
        self.assertTrue(result['allArchiveMembersVerified'])
        self.assertFalse(result['downloadsEnabled'])
        self.assertFalse(result['commercialReleaseApproved'])
        self.assertEqual(result['backendRevision'],self.backend)

    def test_cli_does_not_trust_unapproved_synthetic_publisher_by_default(self):
        self.assertNotEqual(self.trusted,CLINIC_1_0_0.publisher_spki_sha256)
        with self.assertRaisesRegex(VerificationError,'untrusted|Unsigned|unsupported'):
            review_new_release(self.root,self.public,self.archive,self.evidence_path)

    def test_rejects_archive_tamper_even_if_metadata_digest_is_updated(self):
        # Keep the publisher-signed manifest and all signatures unchanged.
        # Rewrite only one unsigned archive member and its OUTER checksum.
        entries={}
        with tarfile.open(self.archive,'r:gz') as t:
            for member in t:
                if member.isfile():
                    with t.extractfile(member) as stream:
                        entries[member.name]=stream.read()
        entries['./frontend/index.html']=b'<html>UNTRUSTED TAMPER</html>'
        with tarfile.open(self.archive,'w:gz') as t:
            for name,data in entries.items():
                item=tarfile.TarInfo(name)
                item.size=len(data)
                t.addfile(item,io.BytesIO(data))
        archive_data=self.archive.read_bytes()
        self.evidence['archiveSha256']=hashlib.sha256(archive_data).hexdigest()
        self.evidence['archiveBytes']=len(archive_data)
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf8')
        with self.assertRaises(VerificationError):
            self.verify()

    def test_rejects_missing_medical_approval_even_with_valid_signature(self):
        self.manifest['approvalReferences'].pop('medicalDirector')
        self.prepare()
        with self.assertRaisesRegex(VerificationError,'approval references'):
            self.verify()

    def test_rejects_mismatched_backend_and_private_frontend_commits(self):
        self.evidence['source']['backendRevision']='f'*40
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf8')
        with self.assertRaisesRegex(VerificationError,'source'):
            self.verify()

    def test_rejects_gateway_activated_metadata_and_wrong_publisher_fingerprint(self):
        self.evidence['gatewayActivated']=True
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf8')
        with self.assertRaisesRegex(VerificationError,'unsupported'):
            self.verify()
        self.evidence['gatewayActivated']=False
        self.evidence['publisherSpkiSha256']='0'*64
        self.evidence_path.write_text(json.dumps(self.evidence),encoding='utf8')
        with self.assertRaisesRegex(VerificationError,'unsupported'):
            self.verify()


    def test_refuses_unsigned_or_mismatched_final_scanner_attestation(self):
        self.manifest['scanEvidenceSha256']='0'*64
        self.prepare()
        with self.assertRaisesRegex(VerificationError,'offline image manifest drift'):
            self.verify()
        self.manifest['scanEvidenceSha256']='e'*64
        self.manifest['reviewedImageIds']['frontend']='sha256:'+'f'*64
        self.prepare()
        with self.assertRaisesRegex(VerificationError,'offline image manifest drift'):
            self.verify()


if __name__=='__main__':
    unittest.main()
