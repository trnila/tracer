import os

from tracer.utils import AttributeTrait


class Syscall(AttributeTrait):
    def __init__(self, process, syscall):
        super().__init__()
        self.process = process
        self.syscall = syscall

    @property
    def result(self):
        return self.syscall.result

    @property
    def arguments(self):
        return self.syscall.arguments

    @property
    def name(self):
        return self.syscall.name


class Descriptor(AttributeTrait):
    READ = 1
    WRITE = 2

    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        self.used = 0
        self.backtrace = None
        self.opened_pid = None

    def get_label(self):
        return ""

    def to_json(self):
        json = self.attributes
        json["type"] = type(self).__name__.lower()
        json["backtrace"] = self.backtrace
        json["opened_pid"] = self.opened_pid

        return json


class Pipe(Descriptor):
    last_pipe = -1

    def __init__(self, fd, pipe_id):
        super().__init__(fd)
        self.pipe_id = pipe_id

    def get_label(self):
        return "pipe: %d" % self.pipe_id

    def to_json(self):
        json = super().to_json()
        json['pipe_id'] = self.pipe_id
        return json

    @staticmethod
    def make_pair(fd1, fd2):
        Pipe.last_pipe += 1

        return (
            Pipe(fd1, Pipe.last_pipe),
            Pipe(fd2, Pipe.last_pipe)
        )


class File(Descriptor):
    def __init__(self, fd, path):
        super().__init__(fd)
        self.path = os.path.realpath(path) if path not in ['stdout', 'stdin', 'stderr'] else path  # TODO: fix
        self.seeks = []
        self.mmaps = []
        self.mode = None

    def get_label(self):
        return self.path.replace('/', '_')

    def to_json(self):
        json = super().to_json()
        json["path"] = self.path
        json['mmap'] = self.mmaps
        json["mode"] = self.mode
        return json


class Socket(Descriptor):
    last_id = -1

    def __init__(self, fd):
        super().__init__(fd)
        self.last_id += 1
        self.label = "socket"
        self.domain = None
        self.type = None
        self.local = None
        self.remote = None
        self.server = False
        self.socket_id = self.last_id
        self.sockopts = []

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
        json['sockopts'] = self.sockopts
        return json
