import struct

from tracer import utils
from tracer.extensions.extension import Extension, register_syscall
from tracer.injector import InjectedMemory


def to_bytes(start, items):
    starts = []
    result = b""
    pointers = b""

    start += (len(items) + 1) * 8
    for item in items:
        starts.append(start)
        result += item
        start += len(item)

    for start in starts:
        pointers += struct.pack("l", start)
    pointers += struct.pack("l", 0)

    return pointers + result


class Execve:
    def __init__(self, syscall):
        # XXX: code dup with core execve
        self.syscall = syscall
        self.program = syscall.arguments[0].text
        proc = syscall.process.tracer.backend.debugger[syscall.process.pid]
        if not proc.syscall_state.syscall:
            raise RuntimeError("Child access")

        self.arguments = utils.parse_args(proc.syscall_state.syscall.arguments[1].text)


# TODO: add support for enviroments
class ReplaceExecve(Extension):
    """
    Replace execve call parameters

    Example:
    Add this function to your configuration file, eg. tracer.conf.py:
    def replace_execve(execve):
        execve.program = "/usr/bin/cut"
        execve.arguments = ["/usr/bin/cut", "-f1", "-d:", "/etc/passwd"]
        return execve

    and call following command
    $ tracer bash -c 'cat /etc/hosts'
    you should see output of all user accounts in your system
    """

    @register_syscall("execve", success_only=False)
    def change(self, syscall):
        if syscall.result:
            return

        try:
            execve = Execve(syscall)
        except RuntimeError:
            return

        fn = getattr(syscall.process.tracer.options, 'replace_execve', None)
        if not fn:
            raise RuntimeError("replace_execve method missing in configuration")

        new = fn(execve)
        if not new:
            return

        new_program = new.program.encode('utf-8') + b"\0"
        offset = len(new_program)
        new_args = [arg.encode('utf-8') + b"\0" for arg in new.arguments]

        addr = InjectedMemory(syscall.process, 10024)

        args_data = to_bytes(addr.addr + offset, new_args)
        addr.write(new_program)
        addr.write(args_data, offset=offset)

        p = syscall.process.tracer.backend.debugger[syscall.process.pid]
        regs = p.getregs()
        regs.rdi = addr.addr
        regs.rsi = addr.addr + offset
        p.setregs(regs)
