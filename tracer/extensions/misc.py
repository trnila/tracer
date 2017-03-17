import struct

from tracer import maps
from tracer.extensions.extension import register_syscall, Extension


class MiscExtension(Extension):
    @register_syscall("kill")
    def kill(self, syscall):
        syscall.process['kills'].append({
            'pid': syscall.arguments[0].value,
            'signal': maps.SIGNALS.get(syscall.arguments[1].value)
        })

    @register_syscall("set_sock_opt")
    def set_sock_opt(self, syscall):
        level = syscall.arguments[1].value
        option_name = syscall.arguments[2].value
        value = \
            struct.unpack("i", syscall.process.read_bytes(syscall.arguments[3].value, syscall.arguments[4].value))[0]

        descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
        descriptor['sockopts'].append({
            "optname": maps.SOCKET_OPTS.get(option_name),
            "level": maps.SOCKET_LEVEL.get(level),
            "value": value,
            "backtrace": syscall.process.get_backtrace()
        })
