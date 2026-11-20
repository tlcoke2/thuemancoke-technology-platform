import json
import unittest
from customer_gateway.release_101_config import approved_release_101, REGIONAL_IDENTITY


def fixture():
    report=dict(REGIONAL_IDENTITY, format='tec-regional-r2-readback/v1',
                fullObjectReadback=True, publisherSignatureVerified=True, etag='a'*32)
    env={'GATEWAY_DOWNLOADS_ENABLED':'true','GATEWAY_RELEASE_APPROVED':'true',
         'GATEWAY_RELEASE_ID':'tec-epr-clinic-1.0.1','GATEWAY_101_BUILD':'regional-a55a2b114a35',
         'GATEWAY_R2_101_EXPECTED_ETAG':'a'*32,
         'GATEWAY_R2_101_READBACK_SHA256':report['archiveSha256'],
         'GATEWAY_LICENCE_SIGNATURE_READBACK_SHA256':report['signatureSha256']}
    for key in ('GATEWAY_OWNER_COMMERCIAL_APPROVAL_REF','GATEWAY_MEDICAL_RELEASE_APPROVAL_REF',
                'GATEWAY_LICENCE_FINAL_UAT_REF','GATEWAY_LICENCE_SECURITY_REVIEW_REF'):
        env[key]='RECORDED-OWNER-EVIDENCE-20261119'
    env['GATEWAY_REGIONAL_R2_READBACK_JSON']=json.dumps(report)
    return env, report


class RegionalReleaseTests(unittest.TestCase):
    def test_exact_readback_selects_only_new_private_object(self):
        env,_=fixture(); release,etag=approved_release_101(env)
        self.assertEqual(release.sha256,REGIONAL_IDENTITY['archiveSha256'])
        self.assertTrue(release.object_key.endswith(REGIONAL_IDENTITY['archiveFilename']))
        self.assertEqual(etag,'a'*32)

    def test_every_readback_identity_is_required_with_exact_types(self):
        _,report=fixture()
        for key in report:
            for bad in (None,False,1,'incorrect'):
                env,r=fixture();r[key]=bad;env['GATEWAY_REGIONAL_R2_READBACK_JSON']=json.dumps(r)
                with self.subTest(key=key,bad=bad), self.assertRaises(ValueError):
                    approved_release_101(env)

    def test_activation_gates_cannot_be_skipped(self):
        env,_=fixture()
        for key in env:
            candidate=env.copy();candidate[key]=''
            with self.subTest(key=key), self.assertRaises(ValueError):
                approved_release_101(candidate)
