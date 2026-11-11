"""No real signing keys, R2 access or production data. Exact schema fakes only."""
import json
import unittest
from release_101_config import approved_release_101, SOURCE_BACKEND, SOURCE_FRONTEND, SOURCE_MANIFEST_SHA256, FINGERPRINT

def fixture():
    images={'backend':'sha256:'+'a'*64,'frontend':'sha256:'+'b'*64,'database':'sha256:'+'c'*64}
    ev={'status':'SIGNED_PENDING_COMMERCIAL_GATEWAY_APPROVAL','releaseVersion':'1.0.1',
        'releaseScope':'FRESH_INSTALLATIONS_ONLY','upgradeSupported':False,'gatewayActivated':False,
        'publisherSpkiSha256':FINGERPRINT,
        'archiveFilename':'TEC-EPR-Clinic-Edition-1.0.1-release-123.tar.gz',
        'archiveSha256':'a'*64,'archiveBytes':400000000,
        'signedManifestSha256':'b'*64,'source':{'backendRevision':SOURCE_BACKEND,'frontendRevision':SOURCE_FRONTEND},
        'imageIds':images}
    rep={'assessment':'VERIFIED_1_0_1_ARCHIVE_PENDING_HUMAN_GATEWAY_APPROVAL',
        'releaseVersion':'1.0.1','releaseScope':'FRESH_INSTALLATIONS_ONLY',
        'upgradeSupported':False,'verifiedArchiveSha256':ev['archiveSha256'],
        'archiveBytes':ev['archiveBytes'],'signedManifestSha256':ev['signedManifestSha256'],
        'publisherSpkiSha256':FINGERPRINT,'backendRevision':SOURCE_BACKEND,
        'frontendRevision':SOURCE_FRONTEND,'candidateManifestSha256':SOURCE_MANIFEST_SHA256,
        'allArchiveMembersVerified':True,'publisherSignatureVerified':True,
        'commercialReleaseApproved':False,'releaseGrantIssued':False,
        'customerLicenseIssued':False,'reviewedImageIds':images}
    env={'GATEWAY_DOWNLOADS_ENABLED':'true','GATEWAY_RELEASE_APPROVED':'true',
         'GATEWAY_RELEASE_ID':'tec-epr-clinic-1.0.1',
         'GATEWAY_R2_101_EXPECTED_ETAG':'f'*32,
         'GATEWAY_R2_101_READBACK_SHA256':ev['archiveSha256'],
         'GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF':'OWNER-APPROVAL-20261111',
         'GATEWAY_MEDICAL_RELEASE_APPROVAL_REF':'MEDICAL-REVIEW-20261111'}
    def pack():
        env['GATEWAY_SIGNED_101_RELEASE_EVIDENCE_JSON']=json.dumps(ev)
        env['GATEWAY_VERIFIED_101_REPORT_JSON']=json.dumps(rep)
        return env
    return env,ev,rep,pack

class ReleaseConfigurationTests(unittest.TestCase):
    def test_exact_101_fresh_only_evidence_returns_private_scoped_release(self):
        env,ev,rep,pack=fixture()
        r,etag=approved_release_101(pack())
        self.assertEqual(r.id,'tec-epr-clinic-1.0.1')
        self.assertEqual(r.bucket,'tec-epr-private-releases')
        self.assertEqual(r.sha256,'a'*64)
        self.assertEqual(etag,'f'*32)
        self.assertEqual(r.object_key,'tec-epr/clinic-edition/1.0.1/'+ev['archiveFilename'])
    def test_cannot_enable_one_switch_or_old_release(self):
        for key,value in [('GATEWAY_DOWNLOADS_ENABLED','false'),('GATEWAY_RELEASE_APPROVED','false'),('GATEWAY_RELEASE_ID','tec-epr-clinic-1.0.0')]:
            with self.subTest(key=key):
                env,ev,rep,pack=fixture();env[key]=value
                with self.assertRaises(ValueError):approved_release_101(pack())
    def test_both_metadata_views_must_match(self):
        for target,key,value in [('ev','releaseScope','ANY_INSTALL'),('ev','upgradeSupported',True),('ev','gatewayActivated',True),('ev','archiveSha256','c'*64),('ev','publisherSpkiSha256','c'*64),('ev','releaseVersion','1.0.0'),('rep','publisherSignatureVerified',False),('rep','allArchiveMembersVerified',False),('rep','candidateManifestSha256','d'*64),('rep','signedManifestSha256','e'*64),('rep','backendRevision','f'*40),('rep','commercialReleaseApproved',True)]:
            with self.subTest(target=target,key=key):
                env,ev,rep,pack=fixture();(ev if target=='ev' else rep)[key]=value
                with self.assertRaises(ValueError):approved_release_101(pack())
    def test_r2_and_human_governance_evidence_must_be_present(self):
        for key,value in [('GATEWAY_R2_101_EXPECTED_ETAG',''),('GATEWAY_R2_101_READBACK_SHA256','0'*64),('GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF','pending'),('GATEWAY_MEDICAL_RELEASE_APPROVAL_REF','synthetic approval')]:
            with self.subTest(key=key):
                env,ev,rep,pack=fixture();env[key]=value
                with self.assertRaises(ValueError):approved_release_101(pack())
    def test_duplicate_json_fields_and_archive_traversal_refused(self):
        env,ev,rep,pack=fixture();pack()
        env['GATEWAY_SIGNED_101_RELEASE_EVIDENCE_JSON']='{"status":"x","status":"y"}'
        with self.assertRaises(ValueError):approved_release_101(env)
        env,ev,rep,pack=fixture();ev['archiveFilename']='../TEC-EPR-Clinic-Edition-1.0.1-hijack.tar.gz'
        with self.assertRaises(ValueError):approved_release_101(pack())

if __name__=='__main__':unittest.main()