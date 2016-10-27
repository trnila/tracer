import ipaddress
import socket

from mmap_tracer import MmapTracer


class Descriptor:
    READ = 1
    WRITE = 2

    def __init__(self, location, fd):
        self.location = location
        self.fd = fd
        self.used = 0

    def get_label(self):
        return ""

    def to_json(self):
        json = {
            "type": type(self).__name__.lower(),
        }

        return json


class Pipe(Descriptor):
    def __init__(self, location, fd, pipe_id):
        super().__init__(location, fd)
        self.pipe_id = pipe_id

    def get_label(self):
        return "pipe: %d" % self.pipe_id

    def to_json(self):
        json = super().to_json()
        json['pipe_id'] = self.pipe_id
        return json


class File(Descriptor):
    def __init__(self, location, fd, path):
        super().__init__(location, fd)
        self.path = path
        self.seeks = []
        self.mmaps = []

    def get_label(self):
        return self.path.replace('/', '_')

    def to_json(self):
        json = super().to_json()
        json["path"] = self.path
        json['mmap'] = self.mmaps
        return json


class Socket(Descriptor):
    def __init__(self, location, fd, socket_id):
        super().__init__(location, fd)
        self.label = "socket"
        self.domain = None
        self.type = None
        self.local = None
        self.remote = None
        self.server = False
        self.socket_id = socket_id

    def get_label(self):
        return 'socket_%d' % self.socket_id

    def to_json(self):
        json = super().to_json()
        json['domain'] = self.domain
        json['socket_type'] = self.type
        json['local'] = self.local
        json['remote'] = self.remote
        json['server'] = self.server
        json['socket_id'] = self.socket_id
        return json


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
