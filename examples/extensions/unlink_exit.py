import mmap

from tracer.extensions.extension import Extension, register_syscall
from tracer.extensions.memory_injector import InjectedMemory

SYSCALL_NOOP = 102  # getuid, NOOP syscall that should have no side effects and no parameters


class ExitOnUnlink(Extension):
    """
    Inject exit code to application that tries to unlink node in filesystem
    This example demonstrates injecting code directly to process and executing it
    Exiting application could be reached by sending sigterm or sigkill

    Usage:
    $ touch /tmp/xxx
    $ tracer -vvvv -e ./examples/extensions/unlink_exit.py rm /tmp/xxx
    Application shall return with exit code 42 and /tmp/xxx should be present on filesystem
    """

    """
        instructions for calling syscall exit(42), can be obtained by calling objdump -S ./obj.o
        b8 3c 00 00 00          mov    $0x3c,%eax
        bf 2a 00 00 00          mov    $0x2a,%edi
        0f 05                   syscall
    """
    EXIT_CODE = b"\xb8\x3c\x00\x00\x00" \
                b"\xbf\x2a\x00\x00\x00" \
                b"\x0f\x05"

    @register_syscall(["unlink", "unlinkat"], success_only=False)
    def fn(self, syscall):
        if syscall.result is not None:
            return

        proc = syscall.process
        addr = InjectedMemory(syscall.process, 1024, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)

        proc.write_bytes(addr.addr, self.EXIT_CODE)

        p = syscall.process.tracer.backend.debugger[syscall.process.pid]
        p.setInstrPointer(addr.addr)
        regs = p.getregs()
        regs.orig_rax = SYSCALL_NOOP
        p.setregs(regs)
