import logging
import mmap
import os
import struct

PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
PAGEMAP_ENTRY = 8


class PageRange:
    def __init__(self, page_size):
        self.page_size = page_size
        self.pages = set()

    def add(self, page):
        self.pages.add(page)

    def get_ranges(self):
        if not self.pages:
            return []

        ranges = []
        sequence = sorted(self.pages)
        start = sequence[0]
        prev = start - self.page_size
        for page in sequence:
            if prev + self.page_size != page:
                ranges.append("%X-%X" % (start, prev))
                start = page
            prev = page

        ranges.append("%X-%X" % (start, prev))

        return ranges

    def not_used(self, start, stop):
        while start <= stop:
            if start not in self.pages:
                yield start
            start += self.page_size


class MmapTracer:
    def __init__(self, pid, start, size, prot, flags):
        self.pid = pid
        self.start = start
        self.size = size
        self.prot = prot
        self.flags = flags
        self.accessed = PageRange(PAGE_SIZE)
        self.region_id = None

    def check(self):
        if not self.flags & mmap.MAP_PRIVATE:
            return

        try:
            with open("/proc/%d/pagemap" % self.pid, 'rb') as file:
                for page in self.accessed.not_used(self.start, self.start + self.size):
                    file.seek(int(page / PAGE_SIZE) * PAGEMAP_ENTRY, 0)
                    val = file.read(8)
                    num = struct.unpack('Q', val)[0]
                    occupied = (num & (1 << 63)) > 0
                    if occupied:
                        self.accessed.add(page)
        except Exception as e:  # TODO: fix
            logging.error("failed reading pagemap %s", e.args)

    def to_json(self):
        return {
            'regions': self.accessed.get_ranges(),
            'region_id': self.region_id
        }
