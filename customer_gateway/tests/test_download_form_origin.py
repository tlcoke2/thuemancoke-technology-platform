import unittest
from sqlalchemy import select
from customer_gateway.tests import test_auth as fixture
from customer_gateway.app import sessions

class DownloadFormOriginTests(unittest.TestCase):
    setUp=fixture.AuthTests.setUp
    tearDown=fixture.AuthTests.tearDown
    start=fixture.AuthTests.start
    finish=fixture.AuthTests.finish
    def test_download_form_retains_same_origin_but_callback_is_suppressed(self):
        self.assertEqual(self.client.get('/api/downloads').headers['referrer-policy'],'same-origin')
        self.assertEqual(self.client.get('/auth/callback').headers['referrer-policy'],'no-referrer')
    def test_null_origin_and_wrong_csrf_remain_denied(self):
        self.finish(self.start())
        with self.engine.connect() as c:
            csrf=c.execute(select(sessions.c.csrf)).scalar_one()
        for origin,token in [('null',csrf),(self.config.origin,'wrong')]:
            r=self.client.post('/api/downloads',headers={'origin':origin},data={'csrf':token,'grant_id':'untrusted','artifact':'signature'})
            self.assertEqual(r.status_code,403)
