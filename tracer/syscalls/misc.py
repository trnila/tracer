import struct

from tracer import maps
from tracer.mmap_tracer import MmapTracer


def Mmap(syscall):
    if syscall.arguments[4].value != 18446744073709551615:
        syscall.process.mmap(syscall.arguments[4].value,
                  MmapTracer(syscall.process['pid'], syscall.result, syscall.arguments[1].value, syscall.arguments[2].value,
                             syscall.arguments[3].value))


def Kill(syscall):
    syscall.process['kills'].append({
        'pid': syscall.arguments[0].value,
        'signal': syscall.arguments[1].value
    })


def SetSockOpt(syscall):
    level = syscall.arguments[1].value
    option_name = syscall.arguments[2].value
    value = struct.unpack("i", syscall.process.handle.readBytes(syscall.arguments[3].value, syscall.arguments[4].value))[0]

    descriptor = syscall.process.descriptors.get(syscall.arguments[0].value)
    descriptor.sockopts.append({
        "optname": maps.sockopts.get(option_name),
        "level": maps.socklevel.get(level),
        "value": value,
        "backtrace": syscall.process.get_backtrace()
    })