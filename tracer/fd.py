import os

from tracer.event import Argument
from tracer.utils import AttributeTrait, build_repr


class Syscall(AttributeTrait):
    def __init__(self, process, syscall):
        super().__init__()
        self.process = process
        self.syscall = syscall
        self.arguments = [Argument(arg) for arg in syscall.arguments]

    @property
    def result(self):
        return self.syscall.result

    @property
    def name(self):
        return self.syscall.name

    @property
    def finished(self):
        return self.result is not None

    @property
    def success(self):
        return self.finished and (self.result >= 0 or self.result == -115)  # Operation now in progress

    def __repr__(self):
        return "<Syscall {}>".format(
            build_repr(self, ['name', 'arguments', 'result'])
        )


class Descriptor(AttributeTrait):
    FILE = 'file'
    PIPE = 'pipe'
    SOCKET = 'socket'

    READ = 1
    WRITE = 2

    last_pipe = -1

    def __init__(self, descriptor_type, fd):
        super().__init__()
        self['type'] = descriptor_type
        self['fd'] = fd
        self.used = 0

    def get_label(self):
        return "{}-{}".format(self['type'], self['fd'])

    def to_json(self):
        json = self.attributes
        return json

    @property
    def fd(self):
        return self['fd']

    @property
    def is_file(self):
        return self['type'] == Descriptor.FILE

    @property
    def is_socket(self):
        return self['type'] == Descriptor.SOCKET

    @property
    def is_pipe(self):
        return self['type'] == Descriptor.PIPE

    @staticmethod
    def create_file(fd, path):
        if path not in ['stdout', 'stdin', 'stderr']:  # TODO: what if file is called stdin?
            path = os.path.realpath(path)

        return Descriptor.create(Descriptor.FILE, fd, path=path)

    @staticmethod
    def create_pipes(fd1, fd2):
        Descriptor.last_pipe += 1

        return (
            Descriptor.create(Descriptor.PIPE, fd1, pipe_id=Descriptor.last_pipe),
            Descriptor.create(Descriptor.PIPE, fd2, pipe_id=Descriptor.last_pipe),
        )

    @staticmethod
    def create_socket(fd):
        return Descriptor.create(Descriptor.SOCKET, fd)

    @staticmethod
    def create(descriptor_type, fd, **kwargs):
        descriptor = Descriptor(descriptor_type, fd)

        for key, value in kwargs.items():
            descriptor[key] = value

        return descriptor
