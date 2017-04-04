import logging
import mmap

from tracer.extensions.extension import Extension

SYSCALL_INSTR_SIZE = 2
SYSCALL_MMAP = 9


def inject_mmap(syscall, length, prot=mmap.PROT_READ | mmap.PROT_WRITE, flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE):
    """
        create address space of length in traced process, returns address in traced process
        currently injecting memory works for process that is *before* syscall, ie. syscall.result returns None
    """
    if syscall.result is not None:
        raise RuntimeError("Process must be before syscall, ie. syscall.result must return None")

    backup = Backup()
    p = syscall.process.tracer.backend.debugger[syscall.process.pid]

    # backup and prepare new register with mmap syscall
    regs = p.getregs()
    backup.backup(regs)
    regs.orig_rax = SYSCALL_MMAP
    regs.rdi = 0
    regs.rsi = length
    regs.rdx = prot
    regs.r10 = flags
    regs.r8 = -1
    regs.r9 = 0

    # set modified registers, resume and wait for syscall
    p.setregs(regs)
    p.syscall()
    p.waitSyscall()

    # get mmap address
    addr = p.getregs().rax

    # set instruction pointer before original syscall, resume and wait
    p.setInstrPointer(p.getInstrPointer() - SYSCALL_INSTR_SIZE)
    p.syscall()
    p.waitSyscall()

    # restore original registers
    backup.restore(regs)
    p.setregs(regs)

    return addr


class Backup:
    def __init__(self):
        self.registers = {}

    def backup(self, regs):
        for prop in dir(regs):
            if not prop.startswith('_'):
                self.registers[prop] = getattr(regs, prop)

    def restore(self, regs):
        for key, val in self.registers.items():
            setattr(regs, key, val)


class MemoryInjectorExtension(Extension):
    """  Extension injects mmap region to each process at start """

    def __init__(self):
        super().__init__()
        self.injected = set()

    def on_syscall(self, syscall):
        if syscall.process.pid not in self.injected:
            addr = inject_mmap(syscall, 1024)
            syscall.process['mem'] = addr
            logging.debug("[%d] our mmap memory located at %X", syscall.process.pid, addr)
            self.injected.add(syscall.process.pid)
