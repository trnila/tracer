import mmap
import os
import struct

page_size = os.sysconf("SC_PAGE_SIZE")
pagemap_entry = 8


class PageRange:
    def __init__(self, size):
        self.size = size
        self.pages = set()

    def add(self, page):
        self.pages.add(page)

    def get_ranges(self):
        if not len(self.pages):
            return []

        ranges = []
        sequence = sorted(self.pages)
        start = sequence[0]
        prev = start - self.size
        for page in sequence:
            if prev + self.size != page:
                ranges.append("%X-%X" % (start, prev))
                start = page
            prev = page

        ranges.append("%X-%X" % (start, prev))

        return ranges


class MmapTracer:
    def __init__(self, pid, start, size, prot, flags):
        self.pid = pid
        self.start = start
        self.size = size
        self.prot = prot
        self.flags = flags
        self.accessed = PageRange(page_size)

    def check(self):
        if not (self.flags & mmap.MAP_PRIVATE):
            return

        with open("/proc/%d/pagemap" % self.pid, 'rb') as file:
            file.seek(int(self.start / page_size) * pagemap_entry, 0)

            end = self.start + self.size
            start = self.start
            while start <= end:
                num = struct.unpack('Q', file.read(8))[0]
                occupied = (num & (1 << 63)) > 0
                if occupied:
                    self.accessed.add(start)

                start += page_size

    def to_json(self):
        return {
            'address': self.start,
            'length': self.size,
            'prot': self.prot,
            'flags': self.flags,
            'regions': self.accessed.get_ranges()
        }

