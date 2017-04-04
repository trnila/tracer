import mmap

import struct

from tracer.extensions.extension import Extension, register_syscall
from tracer.extensions.memory_injector import inject_mmap, Backup

SYSCALL_NOOP = 102  # getuid, NOOP syscall that should have no side effects and no parameters


class InjectWrite(Extension):
    CODE_SET_SYSCALL = b"\xb8\x01\x00\x00\x00"     # mov 1, %eax
    CODE_SET_DESCRIPTOR = b"\xbf\x01\x00\x00\x00"  # mov 1, %edi
    CODE_SET_BUF = b"\x48\xbe"                     # mov ..., %rsi
    CODE_SET_LEN = b"\x48\xba"                     # mov ..., %rdx
    CODE_SYSCALL = b"\x0f\x05"                     # syscall

    @register_syscall("sendfile", success_only=False)
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



        # prepare buffer for text that will be written
        buffer = inject_mmap(syscall, 1024)
        proc.write_bytes(buffer, text)

        # create instructions on fly
        code = self.CODE_SET_SYSCALL + \
               self.CODE_SET_DESCRIPTOR + \
               self.CODE_SET_LEN + struct.pack("<q", len(text)) + \
               self.CODE_SET_BUF + struct.pack("<q", buffer) + \
               self.CODE_SYSCALL

        # prepare region for code
        addr = inject_mmap(syscall, 1024, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
        proc.write_bytes(addr, code)

        p.setInstrPointer(addr)
        regs = p.getregs()
        regs.orig_rax = SYSCALL_NOOP
        p.setregs(regs)

        while p.getInstrPointer() < addr + len(code):
            print(p.getInstrPointer())
            p.singleStep()
            p.waitEvent()

        p.setInstrPointer(orig_ip - 2)
        p.syscall()
        p.waitSyscall()

        regs = p.getregs()
        backup.restore(regs)
        p.setregs(regs)
