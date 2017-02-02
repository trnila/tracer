import socket
from struct import unpack

from tracer import utils, fd
from tracer.fd_resolve import resolve


def handle(descriptor, syscall):
    descriptor.backtrace = syscall.process.get_backtrace()
    descriptor.opened_pid = syscall.process.pid


def handler_execve(syscall):
    syscall.process['executable'] = syscall.arguments[0].text.strip("'")
    syscall.process['arguments'] = utils.parse_args(syscall.arguments[1].text)

    env = dict([i.split("=", 1) for i in utils.parse_args(syscall.arguments[2].text)])
    syscall.process['env'] = env


def handler_open(syscall):
    res = fd.File(syscall.result, syscall.arguments[0].text.strip('\''))
    handle(res, syscall)
    res.mode = syscall.arguments[2].value
    syscall.process.descriptors.open(res)


def handler_socket(syscall):
    descriptor = fd.Socket(syscall.result)
    handle(descriptor, syscall)
    descriptor.domain = syscall.arguments[0].value
    descriptor.type = syscall.arguments[1].value
    syscall.process.descriptors.open(descriptor)


def handler_pipe(syscall):
    pipe_fd = syscall.process.handle.readBytes(syscall.arguments[0].value, 8)
    fd1, fd2 = unpack("ii", pipe_fd)
    pipe1, pipe2 = fd.Pipe.make_pair(fd1, fd2)

    handle(syscall.process.descriptors.open(pipe1), syscall)
    handle(syscall.process.descriptors.open(pipe2), syscall)


def handler_bind(syscall):
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


def handler_connect_like(syscall):  # elif syscall.name in ['connect', 'accept', 'syscall<288>']:
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

        remote_desc = syscall.process.descriptors.open(fd.Socket(fdnum))
        remote_desc.local = syscall.process.descriptors.get(syscall.arguments[0].value).local
    else:
        raise Exception("Unexpected syscall")

    descriptor = syscall.process.descriptors.get(fdnum)
    parsed = utils.parse_addr(bytes_content)
    descriptor.domain = parsed.get_domain()
    descriptor.remote = parsed


def handler_dup2(syscall):
    fildes = syscall.arguments[0].value
    fildes2 = syscall.arguments[1].value

    syscall.process.descriptors.close(fildes2)
    syscall.process.descriptors.clone(fildes2, fildes)


def handler_close(syscall):
    syscall.process.descriptors.close(syscall.arguments[0].value)


def handler_dup_like(syscall):
    new = syscall.result
    old = syscall.arguments[0].value
    syscall.process.descriptors.clone(new, old)


HANDLERS = {
    "open": handler_open,
    "socket": handler_socket,
    "pipe": handler_pipe,
    "bind": handler_bind,
    "connect": handler_connect_like,
    "accept": handler_connect_like,
    "syscall<288>": handler_connect_like,
    "dup2": handler_dup2,
    "dup": handler_dup_like,
    "close": handler_close,
    "fcntl": handler_dup_like,
    "execve": handler_execve
}
