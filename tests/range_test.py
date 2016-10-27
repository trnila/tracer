import unittest

import sys


class RnageTest(unittest.TestCase):
    def test_empty(self):
        r = Range()
        self.assertEqual([], r)


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
