import struct

from tracer import maps
from tracer.mmap_tracer import MmapTracer


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


def SetSockOpt(proc, syscall, tracer):
    level = syscall.arguments[1].value
    option_name = syscall.arguments[2].value
    value = struct.unpack("i", syscall.process.readBytes(syscall.arguments[3].value, syscall.arguments[4].value))[0]

    descriptor = proc.descriptors.get(syscall.arguments[0].value)
    descriptor.sockopts.append({
        "optname": maps.sockopts.get(option_name),
        "level": maps.socklevel.get(level),
        "value": value,
        "backtrace": tracer.backtracer.create_backtrace(syscall.process)
    })