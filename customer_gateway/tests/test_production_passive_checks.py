import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('passive_check',Path(__file__).resolve().parents[2]/'scripts/check-production-gateway.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class PassiveCheckTests(unittest.TestCase):
    def response(self,url,method):
        expected=next(s for path,m,s in checker.CHECKS if url==checker.BASE+path and method==m)
        headers={'cache-control':'no-store','x-content-type-options':'nosniff','x-frame-options':'DENY',
                 'content-security-policy':"default-src 'none'; frame-ancestors 'none'",'strict-transport-security':'max-age=31536000',
                 'content-disposition':'attachment; filename="guide.txt"'}
        body='Request a payment link c4f8c3af8d2e8b97058a8742cc5e5bb8d64b34890e345d12350d6adc0d2f8059'
        return expected,headers,body
    def test_success_means_only_documented_passive_scope(self):
        report=checker.inspect(self.response)
        self.assertTrue(report['pass']);self.assertEqual(len(report['checks']),12)
        self.assertIn('Not a penetration test',report['scope'])
    def test_http_success_on_a_private_route_is_a_failure(self):
        def fetch(url,method):
            status,headers,body=self.response(url,method)
            return (200 if '/admin/' in url else status),headers,body
        self.assertFalse(checker.inspect(fetch)['pass'])
    def test_missing_headers_or_wrong_release_fail(self):
        self.assertFalse(checker.inspect(lambda u,m:(self.response(u,m)[0],{},'wrong release'))['pass'])
