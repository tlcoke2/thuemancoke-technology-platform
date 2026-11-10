import unittest
from unittest.mock import Mock, patch
from customer_gateway.check_private_storage import check, main


class StorageCheckTests(unittest.TestCase):
    def setUp(self):
        self.env=dict(APP_ENV='staging',GATEWAY_DOWNLOADS_ENABLED='false',GATEWAY_RELEASE_APPROVED='false',
                      R2_ACCESS_KEY_ID='synthetic-key',R2_SECRET_ACCESS_KEY='synthetic-secret')
        self.factory=Mock()

    def test_only_head_no_signing(self):
        check(self.env,self.factory)
        self.factory.return_value.check.assert_called_once_with()
        self.factory.return_value.sign.assert_not_called()

    def test_wrong_environment_enabled_flags_and_missing_keys_refused_before_network(self):
        for key,value in (('APP_ENV','production'),('GATEWAY_DOWNLOADS_ENABLED','true'),
                          ('GATEWAY_RELEASE_APPROVED','true'),('GATEWAY_RELEASE_APPROVED','unexpected'),
                          ('R2_SECRET_ACCESS_KEY',''),('R2_ACCESS_KEY_ID',' ')):
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                check(dict(self.env,**{key:value}),self.factory)
        self.factory.assert_not_called()

    def test_failure_does_not_expose_provider_error_or_credentials(self):
        with patch('customer_gateway.check_private_storage.check',side_effect=RuntimeError('secret-value')):
            with self.assertRaises(SystemExit) as error: main()
        self.assertNotIn('secret-value',str(error.exception))
        self.assertIn('No URL generated',str(error.exception))

if __name__=='__main__': unittest.main()
