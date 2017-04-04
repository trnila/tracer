import mmap

from peachpy.x86_64 import MOV, SYSCALL, rax, rdi, rsi, rdx
from tracer.extensions.extension import Extension, register_syscall
from tracer.extensions.memory_injector import Backup, inject_memory

SYSCALL_NOOP = 102  # getuid, NOOP syscall that should have no side effects and no parameters


class InjectWrite(Extension):
    """
    Get content from sendfile syscall
    """

    @register_syscall("sendfile", success_only=False)
    def fn(self, syscall):
        if syscall.result is not None:
            return

        p = syscall.process.tracer.backend.debugger[syscall.process.pid]
        proc = syscall.process
        out_fd = syscall.arguments[0].value
        in_fd = syscall.arguments[1].value
        count = syscall.arguments[3].value

        # backup state before syscall
        orig_ip = p.getInstrPointer()
        backup = Backup()
        backup.backup(p.getregs())

        # prepare buffer of count size for content of whole file
        with inject_memory(syscall.process, count) as buffer:
            # XXX: use return value of read syscall
            # XXX: use buffering
            # XXX: offset
            instrs = [
                MOV(rax, 0),  # read
                MOV(rdi, in_fd),  # descriptor
                MOV(rsi, buffer.addr),
                MOV(rdx, count),
                SYSCALL(),

                MOV(rax, 1),  # write
                MOV(rdi, out_fd),
                MOV(rsi, buffer.addr),
                MOV(rdx, count),
                SYSCALL()
            ]

            code = b"".join([i.encode() for i in instrs])

            # prepare region for code instructions
            with inject_memory(syscall.process, 1024, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC) as addr:
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

                # write content of whole file from memory
                syscall.process.write(out_fd, syscall.process.read_bytes(buffer.addr, count))

                # go back before original syscall
                p.setInstrPointer(orig_ip - 2)
                p.syscall()
                p.waitSyscall()

        # we are before syscall, restore registers
        regs = p.getregs()
        backup.restore(regs)
        p.setregs(regs)

