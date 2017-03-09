import hashlib

from tracer.extensions.extension import Extension, register_syscall
from tracer.mmap_tracer import MmapTracer


def default_capture(region, fd):
    return fd.read(region.size)


class RegionCapture:
    last_id = 0

    def __init__(self, output_dir, process, address, size):
        self.address = address
        self.size = size
        self.last_hash = None
        self.id = RegionCapture.last_id
        self.enable_capture = False
        self.content = "{}/region-{}-{}.".format(output_dir, address, size, self.id)
        self.capture = default_capture
        self.captured_size = size
        self.captured_offset = 0
        self.unmapped = False
        self.descriptor = None
        self.process = process

        RegionCapture.last_id += 1

    def is_active(self):
        return self.enable_capture and not self.unmapped

    def write(self, content):
        m = hashlib.md5()
        m.update(content)
        if m.hexdigest() != self.last_hash:
            self.last_hash = m.hexdigest()
            with open(self.content, "ab") as file:
                file.write(content)

    def to_json(self):
        data = {
            "address": self.address,
            "size": self.size,
            'captured_size': self.captured_size,
            'captured_offset': self.captured_offset,
            'region_id': self.id
        }

        if self.enable_capture:
            data["content"] = self.content

        return data


def get_region(process, address):
    if process['regions']:
        for region in process['regions']:
            if not region.unmapped and region.address == address:
                return region

    return None


class MmapExtension(Extension):
    """
    mmap_filter function
    """

    def create_options(self, parser):
        parser.add_argument('--trace-mmap', action="store_true", default=False)
        parser.add_argument('--save-mmap', action="store_true", default=False)

    @register_syscall("mmap")
    def mmap(self, syscall):
        tracer = syscall.process.tracer
        fd = syscall.arguments[4].value

        start = syscall.result
        size = syscall.arguments[1].value

        capture = RegionCapture(tracer.options.output, syscall.process, start, size)
        if fd != 18446744073709551615:
            capture.descriptor = syscall.process.descriptors.get(fd)

        if tracer.options.mmap_filter:
            result = tracer.options.mmap_filter(capture)
            if isinstance(result, dict):
                def specific_capture(region, fd):
                    if 'offset' in result:
                        fd.seek(result['offset'], 1)

                    return fd.read(result['size'])

                capture.enable_capture = True
                capture.capture = specific_capture

                if 'offset' in result:
                    capture.captured_offset = 0
                capture.captured_size = result['size']
            else:
                capture.enable_capture = result
        else:
            capture.enable_capture = tracer.options.save_mmap
        syscall.process['regions'].append(capture)

        if fd != 18446744073709551615:  # -1
            mmap = MmapTracer(syscall.process['pid'], start, size,
                              syscall.arguments[2].value,
                              syscall.arguments[3].value)

            syscall.process.mmap(syscall.arguments[4].value, mmap)
            mmap.file = syscall.process.descriptors.get(fd)

            mmap.region_id = capture.id

    # TODO: add support for unmaping just part of region
    @register_syscall("munmap")
    def munmap(self, syscall):
        region = get_region(syscall.process, syscall.arguments[0].value)
        if region:
            region.unmapped = True

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
                                if region.is_active():
                                    try:
                                        f.seek(region.address)
                                        region.write(region.capture(region, f))
                                    except Exception as e:
                                        print(e, region.address, region.size)
                except Exception as e:
                    print(e)
