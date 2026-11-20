import os,subprocess,sys,unittest

class RegionalHelpTests(unittest.TestCase):
    def test_regional_help_selects_exact_html_text_and_pdf(self):
        script="""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path
from customer_gateway import customer_help as h
app=FastAPI();h.register(app);c=TestClient(app)
assert h.REGIONAL
for u in ['/help','/help/customer-guide.txt']:
 r=c.get(u);assert r.status_code==200 and h.SHA256 in r.text and '266757194' in r.text
assert h.ARCHIVE.endswith('Regional-a55a2b114a35.tar.gz')
assert c.get('/help/customer-guide.pdf').content==Path(h.__file__).with_name(h.PDF_NAME).read_bytes()
assert 'Jamaica/JMD' in c.get('/help/customer-guide.txt').text
"""
        env=dict(os.environ,GATEWAY_101_BUILD='regional-a55a2b114a35')
        r=subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
