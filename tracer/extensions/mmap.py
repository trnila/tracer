import hashlib
import logging

from tracer import maps
from tracer.extensions.extension import Extension, register_syscall
from tracer.mmap_tracer import MmapTracer


class RegionCapture:
    last_id = 0

    def __init__(self, output_dir, process, address, size, prot=0, flags=0):
        self.address = address
        self.size = size
        self.last_hash = None
        self.id = RegionCapture.last_id
        self.enable_capture = False
        self.content = "{}/region-{}-{}-{}.mmap".format(output_dir, address, size, self.id)
        self.captured_size = size
        self.captured_offset = 0
        self.unmapped = False
        self.descriptor = None
        self.process = process
        self.prot = prot
        self.flags = flags

        RegionCapture.last_id += 1

    def is_active(self):
        return self.enable_capture and not self.unmapped

    def capture(self, fd):
        fd.seek(self.address + self.captured_offset, 1)

        content = fd.read(self.effective_size())
        self._write(content)

    def _write(self, content):
        m = hashlib.md5()
        m.update(content)
        if m.hexdigest() != self.last_hash:
            self.last_hash = m.hexdigest()
            with open(self.content, "ab") as file:
                file.write(content)

    def effective_size(self):
        size = min(self.size, self.captured_size)

        return max(0, size - self.captured_offset)

    def to_json(self):
        data = {
            "address": self.address,
            "size": self.size,
            'captured_size': self.effective_size(),
            'captured_offset': self.captured_offset,
            'region_id': self.id,
            'prot': self.prot,
            'flags': self.flags
        }

        if self.enable_capture:
            data["content"] = self.content

        return data

    @property
    def is_anonymouse(self):
        return 'MAP_ANONYMOUS' in self.flags

    @property
    def is_shared(self):
        return 'MAP_SHARED' in self.flags


def get_region(process, address):
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

    def on_process_created(self, process):
        process['regions'] = []

        if not process.parent:
            return

        for region in process.parent['regions']:
            if region.is_shared:
                process['regions'].append(region)

    @register_syscall("mmap")
    def mmap(self, syscall):
        tracer = syscall.process.tracer
        fd = syscall.arguments[4].value

        start = syscall.result
        size = syscall.arguments[1].value

        capture = RegionCapture(tracer.options.output, syscall.process, start, size)
        capture.prot = maps.MMAP_PROTS.format(syscall.arguments[2].value)
        capture.flags = maps.MMAP_FLAGS.format(syscall.arguments[3].value)

        if not capture.is_anonymouse:  # file backed
            capture.descriptor = syscall.process.descriptors.get(fd)
            self.configure_page_tracer(capture, fd, size, start, syscall)

        self.apply_filter(capture, tracer)

        syscall.process['regions'].append(capture)

    # TODO: add support for unmaping just part of region
    @register_syscall("munmap")
    def munmap(self, syscall):
        region = get_region(syscall.process, syscall.arguments[0].value)
        if region:
            region.unmapped = True

    def configure_page_tracer(self, capture, fd, size, start, syscall):
        """ enable tracing accessed pages in file backed map """
        mmap = MmapTracer(syscall.process['pid'], start, size,
                          syscall.arguments[2].value,
                          syscall.arguments[3].value)
        syscall.process.mmap(syscall.arguments[4].value, mmap)
        mmap.file = syscall.process.descriptors.get(fd)
        mmap.region_id = capture.id

    def apply_filter(self, capture, tracer):
        if 'mmap_filter' in tracer.options:
            result = tracer.options.mmap_filter(capture)
            if isinstance(result, dict):
                if 'offset' in result:
                    capture.captured_offset = result['offset']
                capture.captured_size = result['size']
                capture.enable_capture = True
            else:
                capture.enable_capture = result
        else:
            capture.enable_capture = tracer.options.save_mmap

    def on_tick(self, tracer):
        for pid, proc in tracer.data.processes.items():
            if tracer.options.trace_mmap:
                self.check_read_pages(proc)

            if tracer.options.save_mmap:
                self.capture_content(pid, proc)

    def capture_content(self, pid, proc):
        try:
            with open("/proc/{}/mem".format(pid), 'rb') as f:
                for region in proc['regions']:
                    if region.is_active():
                        try:
                            region.capture(f)
                        except Exception as e:
                            logging.info("mmap capture fail: %s - %s", region.address, str(e))
        except Exception as e:
            logging.info("failed to open mem for pid %s", pid)

    def check_read_pages(self, proc):
        for capture in proc['descriptors']:
            if capture.descriptor.is_file and capture.descriptor['mmap']:
                for mmap_area in capture.descriptor['mmap']:
                    mmap_area.check()
