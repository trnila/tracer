from tracer.backtrace.impl.libunwind import Libunwind
from tracer.extensions.extension import register_syscall, Extension


class Backtrace(Extension):
    def create_options(self, parser):
        parser.add_argument('--backtrace', '-b', help='collect backtraces with libunwind', action="store_true",
                            default=False)

    def on_start(self, tracer):
        if tracer.options.backtrace:
            tracer.backend.backtracer = Libunwind()

    def on_process_exit(self, event):
        event.tracer.backend.backtracer.process_exited(event.process['pid'])

    @register_syscall(["open", "socket"])
    def open_handler(self, syscall):
        descriptor = syscall.process.descriptors.get(syscall.result)

        self._save_backtrace(descriptor, syscall)

    @register_syscall("pipe")
    def pipe_handler(self, syscall):
        self._save_backtrace(
            syscall.process.descriptors.get(syscall['fd1']),
            syscall
        )

        self._save_backtrace(
            syscall.process.descriptors.get(syscall['fd2']),
            syscall
        )

    def _save_backtrace(self, descriptor, syscall):
        descriptor['backtrace'] = syscall.process.get_backtrace()
        descriptor['opened_pid'] = syscall.process.pid
