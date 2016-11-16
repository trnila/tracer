import socket
from struct import unpack

from tracer import fd
from tracer import utils
from tracer.fd_resolve import resolve
from tracer.mmap_tracer import MmapTracer

sockets = 0
pipes = 0

class SyscallHandler:
    def __init__(self):
        self.handlers = {}

    def register(self, syscalls, handler):
        if isinstance(syscalls, str):
            syscalls = [syscalls]

        for syscall in syscalls:
            self.handlers[syscall] = handler

    def handle(self, tracer, syscall):
        if syscall.result >= 0 or syscall.result == -115:
            if syscall.name in self.handlers:
                proc = tracer.data.get_process(syscall.process.pid)
                self.handlers[syscall.name](proc, syscall)


def Open(proc, syscall):
    proc.descriptors.open(fd.File(syscall.result, syscall.arguments[0].text.strip('\'')))

def Socket(proc, syscall):
    descriptor = fd.Socket(syscall.result, sockets)
    descriptor.domain = syscall.arguments[0].value
    descriptor.type = syscall.arguments[1].value
    proc.descriptors.open(descriptor)

    global sockets
    sockets += 1


def Pipe(proc, syscall):
    global pipes

    pipe = syscall.process.readBytes(syscall.arguments[0].value, 8)
    fd1, fd2 = unpack("ii", pipe)
    proc.descriptors.open(fd.Pipe(fd1, pipes))
    proc.descriptors.open(fd.Pipe(fd2, pipes))
    pipes += 1

def Bind(proc, syscall):
    descriptor = proc.descriptors.get(syscall.arguments[0].value)
    bytes_content = syscall.process.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)

    if descriptor.type == 'socket' and descriptor.type == socket.SOCK_DGRAM:
        addr = utils.parse_addr(bytes_content)
        if addr.address.__str__() == "0.0.0.0":
            addr = {
                'address': utils.get_all_interfaces(),
                'port': addr.port
            }
        descriptor.local = addr

    descriptor.server = True
    descriptor.used = 8

def ConnectLike(proc, syscall): #elif syscall.name in ['connect', 'accept', 'syscall<288>']:
    # struct sockaddr { unsigned short family; }
    if syscall.name == 'connect':
        bytes_content = syscall.process.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
        fdnum = syscall.arguments[0].value

        resolved = resolve(syscall.process.pid, fdnum, 1)
        if 'dst' in resolved:
            proc.descriptors.get(fdnum).local = resolved['dst']  # TODO: rewrite
    elif syscall.name in ['accept', 'syscall<288>']:
        bytes_content = syscall.process.readBytes(syscall.arguments[2].value, 4)
        socket_size = unpack("I", bytes_content)[0]
        bytes_content = syscall.process.readBytes(syscall.arguments[1].value, socket_size)
        fdnum = syscall.result

        # mark accepting socket as server
        descriptor = proc.descriptors.get(syscall.arguments[0].value)
        descriptor.server = True
        descriptor.used = 8

        remote_desc = proc.descriptors.open(fd.Socket(fdnum, sockets))
        remote_desc.local = proc.descriptors.get(syscall.arguments[0].value).local
        sockets += 1
    else:
        raise Exception("Unexpected syscall")

    descriptor = proc.descriptors.get(fdnum)
    parsed = utils.parse_addr(bytes_content)
    descriptor.domain = parsed.get_domain()
    descriptor.remote = parsed


def Dup2(proc, syscall):
    a = syscall.arguments[0].value
    b = syscall.arguments[1].value

    proc.descriptors.close(b)
    proc.descriptors.clone(b, a)


def Close(proc, syscall):
    proc.descriptors.close(syscall.arguments[0].value)


def DupLike(proc, syscall):
    new = syscall.result
    old = syscall.arguments[0].value
    proc.descriptors.clone(new, old)


def Mmap(proc, syscall):
    if syscall.arguments[4].value != 18446744073709551615:
        proc.mmap(syscall.arguments[4].value,
                  MmapTracer(proc['pid'], syscall.result, syscall.arguments[1].value, syscall.arguments[2].value,
                             syscall.arguments[3].value))