import struct
import sys
import os

pid = sys.argv[1] if len(sys.argv) > 1 else int(open("/tmp/pid").read())
file = "100mb"

with open("/proc/%d/maps" % pid) as f:
    addr = [i[0].split('-') for i in [i.split() for i in f.read().splitlines()] if len(i) > 5 and file in i[5]][0]


page_size = 4096
pagemap_entry = 8
start = int(addr[0], 16)
end = int(addr[1], 16)


def to_int(str):
    return int("".join(["{0:b}".format(i).ljust(8, '0') for i in str])[::-1], 2)

with open("/proc/%d/pagemap" % pid, 'rb') as f, open("/proc/kpageflags", "rb") as f2:
        f.seek(int(start / page_size) * pagemap_entry, 0)
        i = 0
        while start < end:
            if i % 40 == 0:
                print("\n" + hex(start), end=" ")
                pass
            i += 1
            num = struct.unpack('Q', f.read(8))[0]
            id = num & 0x7FFFFFFFFFFFFF
            print("%d" % ((num & (1 << 63)) > 0), end=" ")

            #print(id)
            #print(hex(id))
            f2.seek(id * 8, 0)
            num = struct.unpack('Q', f2.read(8))[0]
            #print(bin(num))

            start += page_size
