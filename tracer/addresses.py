import socket

import ipaddress


class Address:
    def __init__(self, family):
        self.family = family

    def get_domain(self):
        return self.family

    def to_json(self):
        return self.family


class NetworkAddress:
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def get_domain(self):
        return socket.AF_INET6 if isinstance(self.address, ipaddress.IPv6Address) else socket.AF_INET

    def to_json(self):
        return {
            'address': self.address,
            'port': self.port
        }


class UnixAddress:
    def __init__(self, path):
        self.path = path

    def get_domain(self):
        return socket.AF_UNIX

    def to_json(self):
        return self.path
