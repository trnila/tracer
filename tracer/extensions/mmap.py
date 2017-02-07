from tracer.extensions.extension import Extension, register_syscall
from tracer.mmap_tracer import MmapTracer


class MmapExtension(Extension):
    def create_options(self, parser):
        parser.add_argument('--trace-mmap', action="store_true", default=False)
        parser.add_argument('--save-mmap', action="store_true", default=False)

    @register_syscall("mmap")
    def mmap(self, syscall):
        fd = syscall.arguments[4].value

        if fd != 18446744073709551615:  # -1
            mmap = MmapTracer(syscall.process['pid'], syscall.result, syscall.arguments[1].value,
                              syscall.arguments[2].value,
                              syscall.arguments[3].value)

            syscall.process.mmap(syscall.arguments[4].value, mmap)
            mmap.file = syscall.process.descriptors.get(fd)

    def on_tick(self, tracer):
        if tracer.options.trace_mmap or tracer.options.save_mmap:
            for pid, proc in tracer.data.processes.items():
                for capture in proc['descriptors']:
                    if capture.descriptor.is_file and capture.descriptor['mmap']:
                        for mmap_area in capture.descriptor['mmap']:
                            if tracer.options.trace_mmap:
                                mmap_area.check()
                            if tracer.options.save_mmap:
                                if mmap_area.file['path'].endswith("100mb"):
                                    f = open("/proc/{}/mem".format(mmap_area.pid), 'rb')
                                    f.seek(mmap_area.start)
                                    import code
                                    code.interact(local=locals())