import mmap
import struct

from tracer.extensions.extension import Extension, register_syscall
from tracer.injector import InjectedMemory, Backup

SYSCALL_NOOP = 102  # getuid, NOOP syscall that should have no side effects and no parameters


class InjectWrite(Extension):
    """
    Inject code that does writing to stdout before each mmap and then continue with executing mmap
    """

    CODE_SET_SYSCALL = b"\xb8\x01\x00\x00\x00"     # mov 1, %eax
    CODE_SET_DESCRIPTOR = b"\xbf\x01\x00\x00\x00"  # mov 1, %edi
    CODE_SET_BUF = b"\x48\xbe"                     # mov ..., %rsi
    CODE_SET_LEN = b"\x48\xba"                     # mov ..., %rdx
    CODE_SYSCALL = b"\x0f\x05"                     # syscall

    @register_syscall("mmap", success_only=False)
    def fn(self, syscall):
        if syscall.result is not None:
            return

        p = syscall.process.tracer.backend.debugger[syscall.process.pid]
        proc = syscall.process
        text = b"hello world!\n"

        # backup state before syscall
        orig_ip = p.getInstrPointer()
        backup = Backup()
        backup.backup(p.getregs())

        # prepare buffer for text that will be written to stdout
        buffer = InjectedMemory(syscall.process, 1024)
        proc.write_bytes(buffer.addr, text)

        # create instructions for write(0, buffer, size) on fly
        code = self.CODE_SET_SYSCALL + \
               self.CODE_SET_DESCRIPTOR + \
               self.CODE_SET_LEN + struct.pack("<q", len(text)) + \
               self.CODE_SET_BUF + struct.pack("<q", buffer.addr) + \
               self.CODE_SYSCALL

        # prepare region for code instructions
        addr = InjectedMemory(syscall.process, 1024, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
        proc.write_bytes(addr.addr, code)

        # jump to injected code
        p.setInstrPointer(addr.addr)

        # replace syscall with NOOP syscall
        regs = p.getregs()
        regs.orig_rax = SYSCALL_NOOP
        p.setregs(regs)

        # execute all instructions that we have written to injected memory
        # XXX: performance: maybe we can insert syscall(SIGTRAP)
        while p.getInstrPointer() < addr.addr + len(code):
            p.singleStep()
            p.waitEvent()

        # go back before original syscall
        p.setInstrPointer(orig_ip - 2)
        p.syscall()
        p.waitSyscall()

        # unmap memory in before state
        addr.munmap()
        buffer.munmap()

        # we are before syscall, restore registers
        regs = p.getregs()
        backup.restore(regs)
        p.setregs(regs)