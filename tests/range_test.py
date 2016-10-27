import sys
import unittest

from tracer.mmap_tracer import PageRange


class RangeTest(unittest.TestCase):
    def test_empty(self):
        r = PageRange(8)
        self.assertEqual([], r.get_ranges())

    def test_one(self):
        r = PageRange(8)
        r.add(12345)
        self.assertEqual(['3039-3039'], r.get_ranges())

    def test_one_continuous(self):
        r = PageRange(8)
        r.add(12345)
        r.add(12353)
        self.assertEqual(['3039-3041'], r.get_ranges())

    def test_two_continuous(self):
        r = PageRange(8)
        r.add(5)
        r.add(13)
        r.add(50)
        r.add(58)
        self.assertEqual(['5-D', '32-3A'], r.get_ranges())

    def test_two_longer_continuous(self):
        r = PageRange(8)
        r.add(5)
        r.add(13)
        r.add(21)
        r.add(29)
        r.add(37)
        r.add(50)
        r.add(58)
        self.assertEqual(['5-25', '32-3A'], r.get_ranges())

    def test_one_longer_continuous(self):
        r = PageRange(8)
        r.add(5)
        r.add(13)
        r.add(21)
        r.add(29)
        r.add(37)
        r.add(45)
        r.add(53)
        r.add(61)
        self.assertEqual(['5-3D'], r.get_ranges())


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
