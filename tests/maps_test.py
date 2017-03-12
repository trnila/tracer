import unittest

from tracer.maps import FlaggedDict, DictWithDefault


class MapsTest(unittest.TestCase):
    def test_flagged_empty(self):
        items = FlaggedDict({})
        self.assertEquals([], items.format(15))

    def test_flagged(self):
        items = FlaggedDict({1: 'test', 2: 'test2'})
        self.assertEquals(['test'], items.format(1))
        self.assertEquals(['test2'], items.format(2))
        self.assertEquals(['test', 'test2'], items.format(3))
        self.assertEquals([], items.format(4))

    def test_dict(self):
        items = DictWithDefault({1: 'test', 2: 'test2'})
        self.assertEquals('test', items[1])
        self.assertEquals('test', items.get(1))
        self.assertEquals(3, items[3])
        self.assertEquals(3, items.get(3))
