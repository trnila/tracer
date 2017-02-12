import socket
from struct import unpack

from tracer import utils
from tracer.extensions.extension import register_syscall, Extension
from tracer.fd import Descriptor
from tracer.fd_resolve import resolve


class CoreExtension(Extension):
    @register_syscall("execve")
    def handler_execve(self, syscall):
        syscall.process['executable'] = syscall.arguments[0].text.strip("'")
        syscall.process['arguments'] = utils.parse_args(syscall.arguments[1].text)

        env = dict([i.split("=", 1) for i in utils.parse_args(syscall.arguments[2].text)])
        syscall.process['env'] = env

    @register_syscall("open")
    def handler_open(self, syscall):
        res = Descriptor.create_file(syscall.result, syscall.arguments[0].text.strip('\''))
        res['mode'] = syscall.arguments[2].value
        syscall.process.descriptors.open(res)

    @register_syscall("socket")
    def handler_socket(self, syscall):
        descriptor = Descriptor.create_socket(syscall.result)
        descriptor['domain'] = syscall.arguments[0].value
        descriptor['socket_type'] = syscall.arguments[1].value
        syscall.process.descriptors.open(descriptor)

    @register_syscall("pipe")
    def handler_pipe(self, syscall):
        pipe_fd = syscall.process.read_bytes(syscall.arguments[0].value, 8)
        fd1, fd2 = unpack("ii", pipe_fd)
        pipe1, pipe2 = Descriptor.create_pipes(fd1, fd2)

        syscall['fd1'] = fd1
        syscall['fd2'] = fd2

        syscall.process.descriptors.open(pipe1)
        syscall.process.descriptors.open(pipe2)

    @register_syscall("bind")
    def handler_bind(self, syscall):
        descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
        bytes_content = syscall.process.read_bytes(syscall.arguments[1].value, syscall.arguments[2].value)
        addr = utils.parse_addr(bytes_content)

        if descriptor['socket_type'] == socket.AF_INET and addr.address.__str__() == "0.0.0.0":
            addr = {
                'address': utils.get_all_interfaces(),
                'port': addr.port
            }

        descriptor['local'] = addr

        descriptor['server'] = True
        descriptor.used = 8

    @register_syscall(["connect", "accept", "syscall<288>"])
    def handler_connect_like(self, syscall):  # elif syscall.name in ['connect', 'accept', 'syscall<288>']:
        # struct sockaddr { unsigned short family; }
        if syscall.name == 'connect':
            bytes_content = syscall.process.read_bytes(syscall.arguments[1].value, syscall.arguments[2].value)
            fdnum = syscall.arguments[0].value

            resolved = resolve(syscall.process.pid, fdnum, 1)
            if 'dst' in resolved:
                syscall.process.descriptors.get(fdnum)['local'] = resolved['dst']  # TODO: rewrite
        elif syscall.name in ['accept', 'syscall<288>']:
            bytes_content = syscall.process.read_bytes(syscall.arguments[2].value, 4)
            socket_size = unpack("I", bytes_content)[0]
            bytes_content = syscall.process.read_bytes(syscall.arguments[1].value, socket_size)
            fdnum = syscall.result

            # mark accepting socket as server
            descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
            descriptor['server'] = True
            descriptor.used = 8

            remote_desc = syscall.process.descriptors.open(Descriptor.create_socket(fdnum))
            remote_desc['local'] = syscall.process.descriptors.get(syscall.arguments[0].value)['local']
        else:
            raise Exception("Unexpected syscall")

        descriptor = syscall.process.descriptors.get(fdnum)
        parsed = utils.parse_addr(bytes_content)
        descriptor['domain'] = parsed.get_domain()
        descriptor['remote'] = parsed

    @register_syscall("dup2")
    def handler_dup2(self, syscall):
        fildes = syscall.arguments[0].value
        fildes2 = syscall.arguments[1].value

        syscall.process.descriptors.close(fildes2)
        syscall.process.descriptors.clone(fildes2, fildes)

    @register_syscall("close")
    def handler_close(self, syscall):
        syscall.process.descriptors.close(syscall.arguments[0].value)

    @register_syscall(["dup", "fcntl"])
    def handler_dup_like(self, syscall):
        new = syscall.result
        old = syscall.arguments[0].value
        syscall.process.descriptors.clone(new, old)
