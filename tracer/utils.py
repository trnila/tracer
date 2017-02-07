import ipaddress
import os
import socket
from struct import unpack

from tracer.addresses import UnixAddress, NetworkAddress, Address


def parse_args(string):
    args = []
    capturing = 0
    start = 0

    pos = 0
    for char in string:
        if char == "'":
            if not capturing:
                capturing = 1
                start = pos + 1
            else:
                capturing = 0
                args.append(string[start:pos])

        pos += 1

    return args


def parse_ipv4(raw_bytes):
    try:
        return "%d.%d.%d.%d" % (
            int(raw_bytes[6:8], 16),
            int(raw_bytes[4:6], 16),
            int(raw_bytes[2:4], 16),
            int(raw_bytes[0:2], 16),
        )
    except:
        raise ValueError('Invalid address')


def parse_ipv6(raw_bytes):
    result = ""
    parts = [raw_bytes[i * 8:i * 8 + 8] for i, y in enumerate(raw_bytes[::8])]
    for i in range(0, 4):
        for j in range(0, 4):
            result += format(((int(parts[i], 16) >> (8 * j)) & 0xFF), '02x')
            if j == 1 or j == 3:
                result += ':'

    return ipaddress.ip_address(result.strip(':'))


def parse_addr(address_bytes):
    family = unpack("H", address_bytes[0:2])[0]
    if family == socket.AF_UNIX:
        return UnixAddress(address_bytes[2:].decode('utf-8'))
    elif family in [socket.AF_INET6, socket.AF_INET]:
        port = unpack(">H", address_bytes[2:4])[0]

        if family == socket.AF_INET6:
            addr = ipaddress.ip_address(address_bytes[8:24])
        else:
            addr = ipaddress.ip_address(address_bytes[4:8])

        return NetworkAddress(addr, port)
    else:
        return Address(family)


def get_root():
    return os.path.dirname(os.path.realpath(__file__)) + "/../"


def get_all_interfaces():
    import netifaces
    return [netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr'] for iface in netifaces.interfaces() if
            netifaces.AF_INET in netifaces.ifaddresses(iface)]


# replace with ** when python3.5 used
def merge_dicts(*dicts):
    res = {}
    for dictionary in dicts:
        res.update(dictionary)
    return res


class AttributeTrait:
    def __init__(self):
        self.attributes = {}

    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.attributes[key] = value
