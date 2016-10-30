import mmap
import os
import struct

PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
pagemap_entry = 8


class PageRange:
    def __init__(self, page_size):
        self.page_size = page_size
        self.pages = set()

    def add(self, page):
        self.pages.add(page)

    def get_ranges(self):
        if not len(self.pages):
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

    def check(self):
        if not (self.flags & mmap.MAP_PRIVATE):
            return

        with open("/proc/%d/pagemap" % self.pid, 'rb') as file:
            for page in self.accessed.not_used(self.start, self.start + self.size):
                file.seek(int(page / PAGE_SIZE) * pagemap_entry, 0)
                num = struct.unpack('Q', file.read(8))[0]
                occupied = (num & (1 << 63)) > 0
                if occupied:
                    self.accessed.add(page)

    def to_json(self):
        return {
            'address': self.start,
            'length': self.size,
            'prot': self.prot,
            'flags': self.flags,
            'regions': self.accessed.get_ranges()
        }

