import ipaddress
import socket
from struct import unpack

import fd


def parseArgs(str):
    args = []
    capturing = 0
    start = 0

    pos = 0
    for c in str:
        if c == "'":
            if not capturing:
                capturing = 1
                start = pos + 1
            else:
                capturing = 0
                args.append(str[start:pos])

        pos +=1

    return args


def parse_ipv4(s):
    try:
        return "%d.%d.%d.%d" % (
            int(s[6:8], 16),
            int(s[4:6], 16),
            int(s[2:4], 16),
            int(s[0:2], 16),
        )
    except:
        raise ValueError('Invalid address')

def parse_ipv6(s):
    result = ""
    parts = [s[i * 8:i * 8+8] for i, y in enumerate(s[::8])]
    for i in range(0, 4):
        for j in range(0, 4):
            result += format(((int(parts[i], 16) >> (8*j)) & 0xFF), '02x')
            if j == 1 or j == 3:
                result += ':'

    return ipaddress.ip_address(result.strip(':'))


def parse_addr(bytes):
    family = unpack("H", bytes[0:2])[0]

    if family == socket.AF_UNIX:
        return fd.UnixAddress(bytes[2:].decode('utf-8'))
    elif family in [socket.AF_INET6, socket.AF_INET]:
        port = unpack(">H", bytes[2:4])[0]

        if family == socket.AF_INET6:
            addr = ipaddress.ip_address(bytes[8:24])
        else:
            addr = ipaddress.ip_address(bytes[4:8])

        return fd.NetworkAddress(addr, port)
    else:
        return fd.Address(family)
