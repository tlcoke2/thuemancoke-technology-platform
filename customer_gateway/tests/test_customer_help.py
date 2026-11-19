import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from customer_gateway.customer_help import register, GUIDE, SHA256, ARCHIVE
from customer_gateway.download_policy import LICENCE_1_0_1

class CustomerHelpTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();register(app);self.client=TestClient(app)
    def test_public_guide_matches_approved_archive_and_does_not_request_private_keys(self):
        r=self.client.get('/help')
        self.assertEqual(r.status_code,200)
        self.assertIn('text/html',r.headers['content-type'])
        self.assertIn(LICENCE_1_0_1.sha256,r.text)
        self.assertIn('Install.cmd',r.text)
        self.assertIn('Verify and install',r.text)
        self.assertIn('does not upload',r.text)
        self.assertIn('never need TEC’s private key',r.text)
        self.assertNotIn('<form',r.text)
    def test_download_is_plain_text_with_fixed_filename_and_safe_scope(self):
        r=self.client.get('/help/customer-guide.txt')
        self.assertEqual(r.status_code,200)
        self.assertIn('attachment;',r.headers['content-disposition'])
        self.assertIn('text/plain',r.headers['content-type'])
        self.assertEqual(r.text,GUIDE)
        self.assertIn(LICENCE_1_0_1.publisher_spki_sha256,r.text)
        self.assertIn('does not upload this JSON',' '.join(r.text.split()))
        self.assertIn('not a',r.text)
        self.assertIn('do not',r.text.lower())
        self.assertEqual(ARCHIVE,LICENCE_1_0_1.object_key.rsplit('/',1)[-1])
