import importlib.util
import hashlib
import tempfile
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('gate', Path(__file__).parents[2] / 'scripts/assurance/verify-closeout.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class CloseoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'report.txt').write_text('assessor report fixture')
        self.ref = {'path': 'report.txt', 'sha256': hashlib.sha256((self.root/'report.txt').read_bytes()).hexdigest()}
        self.record = {'format':'tec-closeout-evidence/v1','archiveSha256':gate.ARCHIVE_SHA,'manifestSha256':gate.MANIFEST_SHA,'decisions':[]}
    def decision(self, key):
        return dict(control=key, reviewer='Fixture reviewer',role='Qualified reviewer',decidedAt='2026-11-18T00:00:00Z',scope='fixture',limitations='fixture only',decision='accepted',template=False,independentOfImplementation=True,evidence=[dict(self.ref)])
    def test_empty_is_not_approved(self):
        self.assertFalse(gate.assess(self.record,self.root)['allEvidencePresent'])
    def test_all_attestations_counted_without_certification(self):
        self.record['decisions']=[self.decision(k) for k in gate.REQUIRED]
        result=gate.assess(self.record,self.root)
        self.assertTrue(result['allEvidencePresent'])
        self.assertIn('identity',result['meaning'])
    def test_old_release_rejected(self):
        self.record['manifestSha256']='66907861'
        with self.assertRaises(ValueError): gate.assess(self.record,self.root)
    def test_duplicate_rejected(self):
        self.record['decisions']=[self.decision('clinical')]*2
        with self.assertRaises(ValueError): gate.assess(self.record,self.root)
    def test_tampering_fails(self):
        self.record['decisions']=[self.decision('clinical')]
        (self.root/'report.txt').write_text('changed')
        self.assertNotIn('clinical',gate.assess(self.record,self.root)['acceptedAttestations'])
    def test_template_fails(self):
        d=self.decision('clinical');d['template']=True
        self.record['decisions']=[d]
        self.assertFalse(gate.assess(self.record,self.root)['acceptedAttestations'])
    def test_self_pentest_fails(self):
        d=self.decision('independent_pentest');d['independentOfImplementation']=False
        self.record['decisions']=[d]
        self.assertFalse(gate.assess(self.record,self.root)['acceptedAttestations'])
    def test_traversal_fails(self):
        d=self.decision('clinical');d['evidence'][0]['path']='../outside.txt'
        self.record['decisions']=[d]
        self.assertFalse(gate.assess(self.record,self.root)['acceptedAttestations'])
    def test_missing_roles_fail(self):
        d=self.decision('clinical');del d['role']
        self.record['decisions']=[d]
        self.assertFalse(gate.assess(self.record,self.root)['acceptedAttestations'])
