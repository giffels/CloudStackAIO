from CloudStackAIO.Utilities import add_signature

from unittest import TestCase


class Utilities_t(TestCase):
    def test_add_signature_with_params(self):
        test_params={'test_image': 'vm_image_centos', 'test_disk': 20, 'test_memory': 100.0}
        test_secret='Test'
        test_signature='4eU3C/s4%2BETKxKStBLhgwMPOWXI%3D'

        @add_signature(test_secret)
        def test_function(params):
            self.assertEqual(params['signature'], test_signature)

        test_function(params=test_params)
