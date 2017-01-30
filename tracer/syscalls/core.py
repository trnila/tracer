import socket
from struct import unpack

from tracer import utils, fd
from tracer.fd_resolve import resolve

pipes = 0
sockets = 0

def handle(descriptor, syscall, tracer):
    descriptor.backtrace = tracer.backtracer.create_backtrace(syscall.process)
    descriptor.opened_pid = syscall.process.pid


def Execve(proc, syscall, tracer):
    proc['executable'] = syscall.arguments[0].text.strip("'")
    proc['arguments'] = utils.parse_args(syscall.arguments[1].text)

    env = dict([i.split("=", 1) for i in utils.parse_args(syscall.arguments[2].text)])
    proc['env'] = env


def Open(proc, syscall, tracer):
    res = fd.File(syscall.result, syscall.arguments[0].text.strip('\''))
    handle(res, syscall, tracer)
    res.mode = syscall.arguments[2].value
    proc.descriptors.open(res)


def Socket(proc, syscall, tracer):
    global sockets

    descriptor = fd.Socket(syscall.result, sockets)
    handle(descriptor, syscall, tracer)
    descriptor.domain = syscall.arguments[0].value
    descriptor.type = syscall.arguments[1].value
    proc.descriptors.open(descriptor)

    sockets += 1


def Pipe(proc, syscall, tracer):
    global pipes

    pipe = syscall.process.readBytes(syscall.arguments[0].value, 8)
    fd1, fd2 = unpack("ii", pipe)
    handle(proc.descriptors.open(fd.Pipe(fd1, pipes)), syscall, tracer)
    handle(proc.descriptors.open(fd.Pipe(fd2, pipes)), syscall, tracer)
    pipes += 1


def Bind(proc, syscall, tracer):
    descriptor = proc.descriptors.get(syscall.arguments[0].value)
    bytes_content = syscall.process.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
    addr = utils.parse_addr(bytes_content)

    if descriptor.type == socket.AF_INET and addr.address.__str__() == "0.0.0.0":
        addr = {
            'address': utils.get_all_interfaces(),
            'port': addr.port
        }

    descriptor.local = addr

    descriptor.server = True
    descriptor.used = 8


def ConnectLike(proc, syscall, tracer):  # elif syscall.name in ['connect', 'accept', 'syscall<288>']:
    global sockets

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


def Dup2(proc, syscall, tracer):
    a = syscall.arguments[0].value
    b = syscall.arguments[1].value

    proc.descriptors.close(b)
    proc.descriptors.clone(b, a)


def Close(proc, syscall, tracer):
    proc.descriptors.close(syscall.arguments[0].value)


def DupLike(proc, syscall, tracer):
    new = syscall.result
    old = syscall.arguments[0].value
    proc.descriptors.clone(new, old)