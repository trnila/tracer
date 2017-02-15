import hashlib

from tracer.extensions.extension import Extension, register_syscall
from tracer.mmap_tracer import MmapTracer


class RegionCapture:
    last_id = 0

    def __init__(self, output_dir, address, size):
        self.address = address
        self.size = size
        self.last_hash = None
        self.id = RegionCapture.last_id
        self.content = "{}/region-{}-{}.".format(output_dir, address, size, self.id)

        RegionCapture.last_id += 1

    def write(self, content):
        m = hashlib.md5()
        m.update(content)
        if m.hexdigest() != self.last_hash:
            self.last_hash = m.hexdigest()
            with open(self.content, "ab") as file:
                file.write(content)

    def to_json(self):
        return {
            "address": self.address,
            "size": self.size,
            "content": self.content
        }


class MmapExtension(Extension):
    def create_options(self, parser):
        parser.add_argument('--trace-mmap', action="store_true", default=False)
        parser.add_argument('--save-mmap', action="store_true", default=False)

    @register_syscall("mmap")
    def mmap(self, syscall):
        tracer = syscall.process.tracer
        fd = syscall.arguments[4].value

        start = syscall.result
        size = syscall.arguments[1].value

        capture = RegionCapture(tracer.options.output, start, size)
        syscall.process['regions'].append(capture)

        if fd != 18446744073709551615:  # -1
            mmap = MmapTracer(syscall.process['pid'], start, size,
                              syscall.arguments[2].value,
                              syscall.arguments[3].value)

            syscall.process.mmap(syscall.arguments[4].value, mmap)
            mmap.file = syscall.process.descriptors.get(fd)

            mmap.region_id = capture.id

    def on_tick(self, tracer):
        for pid, proc in tracer.data.processes.items():
            if tracer.options.trace_mmap:
                for capture in proc['descriptors']:
                    if capture.descriptor.is_file and capture.descriptor['mmap']:
                        for mmap_area in capture.descriptor['mmap']:
                                mmap_area.check()

            if tracer.options.save_mmap:
                try:
                    with open("/proc/{}/mem".format(pid), 'rb') as f:
                        if proc['regions']:
                            for region in proc['regions']:
                                try:
                                    f.seek(region.address)
                                    region.write(f.read(region.size))
                                except Exception as e:
                                    print(e)
                                    pass
                except Exception as e:
                    print(e)
