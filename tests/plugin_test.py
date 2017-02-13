import unittest

from tracer.extensions.extension import register_syscall, Extension
from tracer.tracer import Tracer


class FakeExtensions(Extension):
    def __init__(self):
        super().__init__()
        self.start_called = 0
        self.save_called = 0

    def on_start(self, tracer):
        self.start_called += 1

    def on_save(self, tracer):
        self.save_called += 1


class CounterExtension(Extension):
    def __init__(self):
        super().__init__()
        self.called = 0

    @register_syscall("open")
    def somefn(self, syscall):
        self.called += 1


class NonSuccessCalled(Extension):
    def __init__(self):
        super().__init__()
        self.called = 0

    @register_syscall("open", success_only=False)
    def somefn(self, syscall):
        self.called += 1


class PluginTest(unittest.TestCase):
    def _execute(self, extension):  # TODO: mock, do not execute tracing!
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

    def test_success_only_false(self):
        extension = NonSuccessCalled()

        error_syscall = type('FakeSyscall', (object,), {})
        error_syscall.name = 'open'
        error_syscall.result = -5

        success_syscall = type('FakeSyscall', (object,), {})
        success_syscall.name = 'open'
        success_syscall.result = 5

        extension.on_syscall(error_syscall)
        self.assertEqual(1, extension.called)
        extension.on_syscall(success_syscall)
        self.assertEqual(2, extension.called)
