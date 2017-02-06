from tracer import fd
from tracer.extensions.extension import Extension, register_syscall
from tracer.mmap_tracer import MmapTracer


class MmapExtension(Extension):
    def create_options(self, parser):
        parser.add_argument('--trace-mmap', action="store_true", default=False)

    @register_syscall("mmap")
    def mmap(self, syscall):
        if syscall.arguments[4].value != 18446744073709551615:
            syscall.process.mmap(syscall.arguments[4].value,
                                 MmapTracer(syscall.process['pid'], syscall.result, syscall.arguments[1].value,
                                            syscall.arguments[2].value,
                                            syscall.arguments[3].value))

    def on_tick(self, tracer):
        if tracer.options.trace_mmap:
            for pid, proc in tracer.data.processes.items():
                for capture in proc['descriptors']:
                    if capture.descriptor.is_file and capture.descriptor['mmap']:
                        for mmap_area in capture.descriptor['mmap']:
                            mmap_area.check()
