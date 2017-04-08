import sys
import unittest

from tracer import utils
from tracer.utils import FakeObject


class UtilsTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual([], utils.parse_args("<>"))

    def test_simple(self):
        self.assertEqual(['ls'], utils.parse_args("<'ls', NULL>"))

    def test_multiple(self):
        self.assertEqual(['ls', '-l', '/tmp'], utils.parse_args("<'ls', '-l', '/tmp', NULL>"))

    def test_ipv4(self):
        self.assertEqual('93.184.216.34', utils.parse_ipv4('22D8B85D'))
        self.assertEqual('255.255.255.255', utils.parse_ipv4('ffffffff'))
        self.assertEqual('0.0.0.0', utils.parse_ipv4('00000000'))

    def test_ipv4_invalid(self):
        with self.assertRaises(ValueError):
            utils.parse_ipv4('inva')

    def test_ipv6(self):
        self.assertEqual('2606:2800:220:1:248:1893:25c8:1946', str(
            utils.parse_ipv6('0028062601002002931848024619C825')))

    def test_fake_object_list(self):
        obj = FakeObject()
        obj.append("hello")
        obj.append("world")

        self.assertEqual(["hello", "world"], obj.data)
        self.assertTrue("hello" in obj)

    def test_fake_object_dict(self):
        obj = FakeObject()
        obj["hello"] = "world"
        obj["bar"] = "baz"

        self.assertTrue("hello" in obj)
        self.assertEqual("world", obj["hello"])
        self.assertTrue("bar" in obj)
        self.assertEqual("baz", obj["bar"])


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
