import unittest

from tracer.extensions.extension import register_syscall, Extension
from tracer.tracer import Tracer


class FakeExtensions(Extension):
    def __init__(self):
        self.start_called = 0
        self.save_called = 0

    def on_start(self, tracer):
        self.start_called += 1

    def on_save(self, tracer):
        self.save_called += 1


class CounterExtension(Extension):
    def __init__(self):
        self.called = 0

    @register_syscall("open")
    def somefn(self, syscall):
        self.called += 1


class MmapTest(unittest.TestCase):
    def _execute(self, extension):
        # TODO: fix this
        import sys
        sys.argv = ['app', '-o', '/tmp/report_', 'ls']
        app = Tracer()
        app.register_extension(extension)

        app.main()

    def test_start_save_called(self):
        ext = FakeExtensions()
        self._execute(ext)

        self.assertEqual(1, ext.start_called)
        self.assertEqual(1, ext.save_called)

    def test_open_called(self):
        ext = CounterExtension()
        self._execute(ext)

        self.assertNotEqual(0, ext.called)
