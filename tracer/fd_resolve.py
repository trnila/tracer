import os
import re

from tracer import utils


def resolve_socket(inode, read):
    files = [
        ('/proc/net/tcp', utils.parse_ipv4),
        ('/proc/net/udp', utils.parse_ipv4),
        ('/proc/net/tcp6', utils.parse_ipv6),
        ('/proc/net/udp6', utils.parse_ipv6)
    ]

    for file_location, addr_resolver in files:
        with open(file_location) as file:
            content = file.read().splitlines()[1:]
            for i in content:
                parts = i.split()
                if parts[9] == inode:
                    ip, port = parts[1 if read else 2].split(':')
                    ip2, port2 = parts[2 if read else 1].split(':')

                    return {
                        "type": "socket",
                        "id": "".join(sorted([ip, port, ip2, port2])),
                        "dst": {
                            "address": addr_resolver(ip),
                            "port": int(port, 16)
                        },
                        "src": {
                            "address": addr_resolver(ip2),
                            "port": int(port2, 16)
                        }
                    }

    with open('/proc/net/unix') as file:
        content = file.read().splitlines()[1:]
        for i in content:
            parts = i.split()
            if parts[6] == inode:
                path = parts[7] if len(parts) > 7 else None
                return {
                    "type": "socket",
                    'id': inode,
                    "path": path
                }


def resolve(pid, fd, read):
    dst = os.readlink("/proc/" + str(pid) + "/fd/" + str(fd))
    match = re.search(r'^(?P<type>socket|pipe):\[(?P<inode>\d+)\]$', dst)

    if not match:
        return {
            'type': 'file',
            'id': dst.replace('/', '_'),
            'file': dst
        }

    fd_type = match.group('type')
    inode = match.group('inode')
    if fd_type == 'pipe':
        return {
            'type': 'pipe',
            'id': inode,
            'inode': inode
        }
    elif fd_type == 'socket':
        a = resolve_socket(inode, read)
        if a:
            return a

    return {
        'type': 'unknown',
        'id': 'unknown'
    }
