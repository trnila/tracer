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
                self.handlers[syscall.name](proc, syscall, tracer)


def Execve(proc, syscall, tracer):
    proc['executable'] = syscall.arguments[0].text.strip("'")
    proc['arguments'] = utils.parse_args(syscall.arguments[1].text)

    env = dict([i.split("=", 1) for i in utils.parse_args(syscall.arguments[2].text)])
    proc['env'] = env


def Open(proc, syscall, tracer):
    res = fd.File(syscall.result, syscall.arguments[0].text.strip('\''))
    res.mode = syscall.arguments[2].value
    proc.descriptors.open(res)


def Socket(proc, syscall, tracer):
    descriptor = fd.Socket(syscall.result, sockets)
    descriptor.domain = syscall.arguments[0].value
    descriptor.type = syscall.arguments[1].value
    proc.descriptors.open(descriptor)

    global sockets
    sockets += 1


def Pipe(proc, syscall, tracer):
    global pipes

    pipe = syscall.process.readBytes(syscall.arguments[0].value, 8)
    fd1, fd2 = unpack("ii", pipe)
    proc.descriptors.open(fd.Pipe(fd1, pipes))
    proc.descriptors.open(fd.Pipe(fd2, pipes))
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


def Mmap(proc, syscall, tracer):
    if syscall.arguments[4].value != 18446744073709551615:
        proc.mmap(syscall.arguments[4].value,
                  MmapTracer(proc['pid'], syscall.result, syscall.arguments[1].value, syscall.arguments[2].value,
                             syscall.arguments[3].value))


def Kill(proc, syscall, tracer):
    proc['kills'].append({
        'pid': syscall.arguments[0].value,
        'signal': syscall.arguments[1].value
    })


def ReadOrWrite(proc, syscall, tracer):
    descriptor = proc.descriptors.get(syscall.arguments[0].value)
    if isinstance(descriptor, fd.Socket) and descriptor.domain in [socket.AF_INET, socket.AF_INET6]:
        try:
            if descriptor.local.address.__str__() == '0.0.0.0':
                resolved = resolve(syscall.process.pid, syscall.arguments[0].value, 1)
                descriptor.local = resolved['dst']
        except:
            pass

    family = {
        "read": "read",
        "write": "write",
        "sendmsg": "write",
        "recvmsg": "read",
        "sendto": "write",
        "recvfrom": "read"
    }[syscall.name]

    content = b""

    if syscall.name in ['sendmsg', 'recvmsg']:
        bytes_content = syscall.process.readBytes(syscall.arguments[1].value, 32)
        items = unpack("PIPL", bytes_content)

        for i in range(0, items[3]):
            bytes_content = syscall.process.readBytes(items[2] + 16 * i, 16)
            i = unpack("PL", bytes_content)
            content += syscall.process.readBytes(i[0], i[1])
    else:
        wrote = syscall.result if family == 'read' else syscall.arguments[2].value
        content = syscall.process.readBytes(syscall.arguments[1].value, wrote)

    data = {
        "backtrace": tracer.backtracer.create_backtrace(syscall.process)
    }
    if syscall.name in ['recvfrom', 'sendto'] and descriptor.type in [socket.SOCK_DGRAM]:
        # TODO: read addr, IPV6 support!
        # sock_size = syscall.process.readWord(syscall.arguments[5].value)

        des = proc.descriptors.get(syscall.arguments[0].value)
        if not des.local:
            addr = resolve(syscall.process.pid, syscall.arguments[0].value, 1)['dst']
            if addr['address'].__str__() == "0.0.0.0":
                addr = {
                    'address': utils.get_all_interfaces(),
                    'port': addr['port']
                }
            des.local = addr

        addr = utils.parse_addr(syscall.process.readBytes(syscall.arguments[4].value, 8))
        data['address'] = addr
        import base64
        data['_'] = base64.b64encode(content).decode('utf-8')

    if family == 'read':
        proc.read(syscall.arguments[0].value, content, **data)
    else:
        proc.write(syscall.arguments[0].value, content, **data)
