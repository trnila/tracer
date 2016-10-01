import ipaddress
import socket


class Descriptor:
    READ = 1
    WRITE = 2

    def __init__(self, location, fd):
        self.location = location
        self.fd = fd
        self.id = str(id(self))
        self.used = 0

    def getLabel(self):
        return ""

    def getId(self):
        return None

    def read(self, data):
        self.used |= Descriptor.READ
        self.location.append_file(self.id + "_read", data)

    def write(self, data):
        self.used |= Descriptor.WRITE
        self.location.append_file(self.id + "_write", data)

    def to_json(self):
        json = {
            "type": type(self).__name__.lower(),
        }

        if self.used & Descriptor.READ:
            json['read_content'] = self.id + "_read"

        if self.used & Descriptor.WRITE:
            json['write_content'] = self.id + "_write"

        return json


class Pipe(Descriptor):
    def __init__(self, location, fd):
        super().__init__(location, fd)

    def getLabel(self):
        return "pipe"


class File(Descriptor):
    def __init__(self, location, fd, path):
        super().__init__(location, fd)
        self.path = path
        self.seeks = []

    def getLabel(self):
        return self.path

    def to_json(self):
        json = super().to_json()
        json["path"] = self.path
        return json


class Socket(Descriptor):
    def __init__(self, location, fd):
        super().__init__(location, fd)
        self.label = "socket"
        self.family = None
        self.local = None
        self.remote = None
        self.server = False

    def getLabel(self):
        if self.family in [socket.AF_INET, socket.AF_INET6]:
            return "%s:%s" % (self.addr, self.port)
        return self.addr

    def to_json(self):
        json = super().to_json()
        json['family'] = self.family
        json['local'] = self.local
        json['remote'] = self.remote
        json['server'] = self.server
        return json


class Address:
    def __init__(self, family):
        self.family = family

    def get_family(self):
        return self.family

    def to_json(self):
        return self.family


class NetworkAddress:
    def __init__(self, address, port):
        self.address = address
        self.port = port

    def get_family(self):
        return socket.AF_INET6 if isinstance(self.address, ipaddress.IPv6Address) else socket.AF_INET

    def to_json(self):
        return {
            'address': self.address,
            'port': self.port
        }


class UnixAddress:
    def __init__(self, path):
        self.path = path

    def get_family(self):
        return socket.AF_UNIX

    def to_json(self):
        return self.path
