import contextlib
import inspect
import logging
import mmap

SYSCALL_INSTR_SIZE = 2
SYSCALL_MMAP = 9
SYSCALL_MUNMAP = 11
REGISTERS = [
    'rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9'
]


def inject_syscall(proc, new_syscall, arguments=None):
    """
    inject syscall to traced process
    currently injecting memory works for process that is *before* syscall, ie. syscall.result returns None
    """

    if arguments is None:
        arguments = []

    process = proc.tracer.backend.debugger[proc.pid]

    if not process.syscall_state.syscall:
        raise RuntimeError("No active syscall")

    if process.syscall_state.syscall.result is not None:
        raise RuntimeError("Process must be before syscall, ie. syscall.result must return None")

    regs = process.getregs()

    # backup all registers that will be restored when injected syscall completes
    backup = Backup()
    backup.backup(regs)

    regs.orig_rax = new_syscall
    for reg, val in zip(REGISTERS, arguments):
        setattr(regs, reg, val)
    process.setregs(regs)

    # set modified registers, resume and wait for syscall
    process.setregs(regs)
    process.syscall()
    process.waitSyscall()

    result = process.getregs().rax

    # set instruction pointer before original syscall, resume and wait
    process.setInstrPointer(process.getInstrPointer() - SYSCALL_INSTR_SIZE)
    process.syscall()
    process.waitSyscall()

    # restore original registers
    backup.restore(regs)
    process.setregs(regs)
    return result


@contextlib.contextmanager
def inject_memory(*kargs, **kwargs):
    """
    When python leaves with context, process *MUST* be in pre syscall state!
    """
    mem = InjectedMemory(*kargs, **kwargs)
    yield mem
    mem.munmap()


class InjectedMemory:
    def __init__(
            self,
            process,
            length,
            prot=mmap.PROT_READ | mmap.PROT_WRITE,
            flags=mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE):
        self.length = length
        self.process = process
        self.mapped = True
        self.caller_frame = inspect.stack()[1]

        parameters = [0, length, prot, flags, -1, 0]
        self.addr = inject_syscall(process, SYSCALL_MMAP, parameters)

    def munmap(self):
        inject_syscall(self.process, SYSCALL_MUNMAP, [self.addr, self.length])
        self.mapped = False

    def write(self, content, offset=0):
        self.process.write_bytes(self.addr + offset, content)

    def read(self):
        return self.process.read_bytes(self.addr, self.length)

    def __del__(self):
        if self.mapped:
            logging.warning(
                "Mapped region left in process, %s:%d (%s)",
                self.caller_frame.filename,
                self.caller_frame.lineno,
                self.caller_frame.function
            )


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