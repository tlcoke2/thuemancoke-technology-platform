import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
spec=importlib.util.spec_from_file_location('collector',Path(__file__).parents[2]/'scripts/assurance/collect-cloudflare.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
class Response:
    def __init__(self,data): self.raw=json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,limit): return self.raw[:limit]
class CloudflareTests(unittest.TestCase):
    def test_invalid_zone_never_sends(self):
        with patch.object(collector.urllib.request,'build_opener') as opener:
            with self.assertRaises(ValueError): collector.collect('../elsewhere','secret')
            opener.assert_not_called()
    def test_only_get_and_secret_absent_from_evidence(self):
        class Opener:
            def open(self,req,timeout):
                self_outer.assertEqual(req.get_method(),'GET')
                self_outer.assertTrue(req.full_url.startswith('https://api.cloudflare.com/client/v4/zones/'+'a'*32))
                result=[] if req.full_url.endswith('/rulesets') else {'id':'fixture','value':'on','token':'secret'}
                return Response({'success':True,'result':result})
        self_outer=self
        with patch.object(collector.urllib.request,'build_opener',return_value=Opener()):
            result=collector.collect('a'*32,'secret')
        self.assertTrue(result['allReadsSucceeded'])
        self.assertNotIn('secret',json.dumps(result))
        self.assertFalse(result['effectiveBlockingVerified'])
        self.assertFalse(result['alertDeliveryVerified'])
    def test_forbidden_remains_unverified(self):
        with patch.object(collector.urllib.request,'build_opener') as build:
            build.return_value.open.side_effect=HTTPError('https://api.cloudflare.com',403,'denied',{},None)
            result=collector.collect('a'*32,'secret')
        self.assertFalse(result['allReadsSucceeded'])
        self.assertTrue(all(c['httpStatus']==403 for c in result['checks'].values()))
    def test_api_error_does_not_leak_response(self):
        with patch.object(collector.urllib.request,'build_opener') as build:
            build.return_value.open.return_value=Response({'success':False,'errors':['secret']})
            result=collector.collect('a'*32,'secret')
        self.assertFalse(result['allReadsSucceeded'])
        self.assertNotIn('secret',json.dumps(result))
