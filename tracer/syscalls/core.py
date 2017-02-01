import socket
from struct import unpack

from tracer import utils, fd
from tracer.fd_resolve import resolve

pipes = 0
sockets = 0


def handle(descriptor, syscall):
    descriptor.backtrace = syscall.process.get_backtrace()
    descriptor.opened_pid = syscall.process.pid


def Execve(syscall):
    syscall.process['executable'] = syscall.arguments[0].text.strip("'")
    syscall.process['arguments'] = utils.parse_args(syscall.arguments[1].text)

    env = dict([i.split("=", 1) for i in utils.parse_args(syscall.arguments[2].text)])
    syscall.process['env'] = env


def Open(syscall):
    res = fd.File(syscall.result, syscall.arguments[0].text.strip('\''))
    handle(res, syscall)
    res.mode = syscall.arguments[2].value
    syscall.process.descriptors.open(res)


def Socket(syscall):
    global sockets

    descriptor = fd.Socket(syscall.result, sockets)
    handle(descriptor, syscall)
    descriptor.domain = syscall.arguments[0].value
    descriptor.type = syscall.arguments[1].value
    syscall.process.descriptors.open(descriptor)

    sockets += 1


def Pipe(syscall):
    global pipes

    pipe = syscall.process.handle.readBytes(syscall.arguments[0].value, 8)
    fd1, fd2 = unpack("ii", pipe)
    handle(syscall.process.descriptors.open(fd.Pipe(fd1, pipes)), syscall)
    handle(syscall.process.descriptors.open(fd.Pipe(fd2, pipes)), syscall)
    pipes += 1


def Bind(syscall):
    descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
    bytes_content = syscall.process.handle.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
    addr = utils.parse_addr(bytes_content)

    if descriptor.type == socket.AF_INET and addr.address.__str__() == "0.0.0.0":
        addr = {
            'address': utils.get_all_interfaces(),
            'port': addr.port
        }

    descriptor.local = addr

    descriptor.server = True
    descriptor.used = 8


def ConnectLike(syscall):  # elif syscall.name in ['connect', 'accept', 'syscall<288>']:
    global sockets

    # struct sockaddr { unsigned short family; }
    if syscall.name == 'connect':
        bytes_content = syscall.process.handle.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
        fdnum = syscall.arguments[0].value

        resolved = resolve(syscall.process.pid, fdnum, 1)
        if 'dst' in resolved:
            syscall.process.descriptors.get(fdnum).local = resolved['dst']  # TODO: rewrite
    elif syscall.name in ['accept', 'syscall<288>']:
        bytes_content = syscall.process.handle.readBytes(syscall.arguments[2].value, 4)
        socket_size = unpack("I", bytes_content)[0]
        bytes_content = syscall.process.handle.readBytes(syscall.arguments[1].value, socket_size)
        fdnum = syscall.result

        # mark accepting socket as server
        descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
        descriptor.server = True
        descriptor.used = 8

        remote_desc = syscall.process.descriptors.open(fd.Socket(fdnum, sockets))
        remote_desc.local = syscall.process.descriptors.get(syscall.arguments[0].value).local
        sockets += 1
    else:
        raise Exception("Unexpected syscall")

    descriptor = syscall.process.descriptors.get(fdnum)
    parsed = utils.parse_addr(bytes_content)
    descriptor.domain = parsed.get_domain()
    descriptor.remote = parsed


def Dup2(syscall):
    a = syscall.arguments[0].value
    b = syscall.arguments[1].value

    syscall.process.descriptors.close(b)
    syscall.process.descriptors.clone(b, a)


def Close(syscall):
    syscall.process.descriptors.close(syscall.arguments[0].value)


def DupLike(syscall):
    new = syscall.result
    old = syscall.arguments[0].value
    syscall.process.descriptors.clone(new, old)


handlers = {
    "open": Open,
    "socket": Socket,
    "pipe": Pipe,
    "bind": Bind,
    "connect": ConnectLike,
    "accept": ConnectLike,
    "syscall<288>": ConnectLike,
    "dup2": Dup2,
    "dup": DupLike,
    "close": Close,
    "fcntl": DupLike,
    "execve": Execve
}
