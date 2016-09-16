import os
import platform
import re

import utils


def resolve_socket(inode, read):
    with open('/proc/net/tcp') as file:
        content = file.read().splitlines()[1:]
        for i in content:
            parts = i.split()
            print(parts)
            if parts[9] == inode:
                ip, port = parts[1 if read else 2].split(':')
                ip2, port2 = parts[2 if read else 1].split(':')

                return {
                    "type": "socket",
                    "dst": {
                        "address": utils.parse_ipv4(ip),
                        "port": int(port, 16)
                    },
                    "src": {
                        "address": utils.parse_ipv4(ip2),
                        "port": int(port2, 16)
                    }
                }


def resolve(pid, fd, read):
    if 'bsd' in platform.system().lower():
        # TODO: use procstat
        return str(fd)

    dst = os.readlink("/proc/" + str(pid) + "/fd/" + str(fd))
    match = re.search('^(?P<type>socket|pipe):\[(?P<inode>\d+)\]$', dst)

    if not match:
        return {
            'type': 'file',
            'file': dst
        }

    type = match.group('type')
    inode = match.group('inode')
    if type == 'pipe':
        return {
            'type': 'pipe',
            'inode': inode
        }
    elif type == 'socket':
        a = resolve_socket(inode, read)
        if a:
            return a

    return {}
