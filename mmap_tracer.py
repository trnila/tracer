import mmap

page_size = 4096
pagemap_entry = 8


class MmapTracer:
    def __init__(self, pid, start, size, prot, flags):
        self.start = start
        self.size = size
        self.prot = prot
        self.flags = flags
        self.file = open("/proc/%d/pagemap" % pid, 'rb')
        self.accessed = set()

    def check(self):
        if not (self.flags & mmap.MAP_PRIVATE):
            return

        self.file.seek(int(self.start / page_size) * pagemap_entry, 0)
        i = 0

        end = self.start + self.size
        while self.start < end:
            if i % 40 == 0:
                #print("\n" + hex(self.start), end=" ")
                pass
            i += 1
            buf = self.file.read(pagemap_entry)
            #print("%d" % (buf[7] & 1), end=" ")
            if buf[7] & 1:
                self.accessed.add(self.start)

            self.start += page_size

    def to_json(self):
        return {
            'address': self.start,
            'length': self.size,
            'prot': self.prot,
            'flags': self.flags,
            'regions': list(self.accessed)
        }


#with open("/proc/%d/pagemap" % pid, 'rb') as f:
#    mmap = Mmap(f, start, end)
#    mmap.check()



