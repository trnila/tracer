from struct import unpack

from tracer import utils
from tracer.extensions.extension import register_syscall, Extension
from tracer.fd_resolve import resolve


class ContentsExtension(Extension):
    @register_syscall(["read", "write", "sendmsg", "recvmsg", "sendto", "recvfrom"])
    def read_or_write(self, syscall):
        descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
        if descriptor.ignored:
            return

        if descriptor.is_socket and descriptor['domain'] in ['AF_INET', 'AF_INET6']:
            try:
                if descriptor['local'].address.__str__() == '0.0.0.0':
                    resolved = resolve(syscall.process.pid, syscall.arguments[0].value, 1)
                    descriptor['local'] = resolved['dst']
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
            bytes_content = syscall.process.read_bytes(syscall.arguments[1].value, 32)
            items = unpack("PIPL", bytes_content)

            for i in range(0, items[3]):
                bytes_content = syscall.process.read_bytes(items[2] + 16 * i, 16)
                i = unpack("PL", bytes_content)
                content += syscall.process.read_bytes(i[0], i[1])
        else:
            wrote = syscall.result if family == 'read' else syscall.arguments[2].value
            content = syscall.process.read_bytes(syscall.arguments[1].value, wrote)

        data = {
            "backtrace": syscall.process.get_backtrace()
        }
        if syscall.name in ['recvfrom', 'sendto'] and descriptor['socket_type'] == 'SOCK_DGRAM':
            # TODO: read addr, IPV6 support!
            # sock_size = syscall.process.readWord(syscall.arguments[5].value)

            des = syscall.process.descriptors.get(syscall.arguments[0].value)
            if not des['local']:
                addr = resolve(syscall.process.pid, syscall.arguments[0].value, 1)['dst']
                if addr['address'].__str__() == "0.0.0.0":
                    addr = {
                        'address': utils.get_all_interfaces(),
                        'port': addr['port']
                    }
                des['local'] = addr

            addr = utils.parse_addr(syscall.process.read_bytes(syscall.arguments[4].value, 8))
            data['address'] = addr
            import base64
            data['_'] = base64.b64encode(content).decode('utf-8')

        if family == 'read':
            syscall.process.read(syscall.arguments[0].value, content, **data)
        else:
            syscall.process.write(syscall.arguments[0].value, content, **data)
