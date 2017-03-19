import unittest

from tracer.extensions.mmap import RegionCapture


def create_capture(size):
    return RegionCapture(0, 0, 0, size)


class QueriesTest(unittest.TestCase):
    def test_effective_size_basic(self):
        capture = create_capture(8192)

        self.assertEqual(8192, capture.effective_size())

    def test_effective_size_bigger(self):
        capture = create_capture(8192)
        capture.captured_size = 10000

        self.assertEqual(8192, capture.effective_size())

    def test_effective_size_smaller(self):
        capture = create_capture(8192)
        capture.captured_size = 1

        self.assertEqual(1, capture.effective_size())

    def test_effective_size_offset_none(self):
        capture = create_capture(8192)
        capture.captured_offset = 8192

        self.assertEqual(0, capture.effective_size())

    def test_effective_size_offset_bigger(self):
        capture = create_capture(8192)
        capture.captured_offset = 10000

        self.assertEqual(0, capture.effective_size())

    def test_effective_size_offset(self):
        capture = create_capture(8192)
        capture.captured_offset = 8000

        self.assertEqual(192, capture.effective_size())
