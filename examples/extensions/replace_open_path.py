import argparse
import logging

import mmap

from tracer.extensions.extension import Extension, register_syscall


class StoreToDict(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not getattr(namespace, self.dest):
            setattr(namespace, self.dest, {})

        pair = values.split(':', 2)
        if len(pair) != 2:
            raise argparse.ArgumentError(self, "must have two values separated by colon, '{}' given".format(values))

        val = getattr(namespace, self.dest)
        val[pair[0]] = pair[1]


class ChangeOpenPath(Extension):
    def create_options(self, parser):
        parser.add_argument(
            '--replace-path',
            action=StoreToDict,
            help='Replace path1 with path2 in open syscalls, --replace-path path1:path2',
            default={}
        )

    #@register_syscall("open", success_only=False)
    def change(self, syscall):
        paths = syscall.process.tracer.options.replace_path
        requested_path = syscall.arguments[0].text

        if syscall.name != "open" or syscall.result or requested_path not in paths:
            return

        new_path = paths[requested_path]
        logging.info("Replacing path %s with %s", requested_path, new_path)

        addr = syscall.arguments[0].value
        syscall.process.write_bytes(addr, new_path.encode('utf-8') + b'\0')


# d=syscall.process.tracer.backend.debugger
# d[process.pid].setInstrPointer(0x555555554000 + 0x7f0)
# d[process.pid].cont()

class Backup:
    def __init__(self):
        self.registers = {}

    def backup(self, regs):
        for prop in dir(regs): #['orig_rax', 'rdi', 'rsi', 'rdx', 'r10', 'r8', 'r9']: #dir(regs):
            if not prop.startswith('_'):
                self.registers[prop] = getattr(regs, prop)

    def restore(self, regs):
        for key, val in self.registers.items():
            setattr(regs, key, val)

class Test(Extension):
    def __init__(self):
        super().__init__()
        self.injected = set()

    def on_syscall(self, syscall):
        if syscall.name != 'open' or syscall.arguments[0].text != "/etc/passwd" or syscall.result is not None:
            return


        backup = Backup()
        if syscall.process.pid not in self.injected:
            p=syscall.process.tracer.backend.debugger[syscall.process.pid]

            pre = p.getInstrPointer()
            print(hex(p.getInstrPointer()))

            # backup and prepare new register with mmap syscall
            regs = p.getregs()
            backup.backup(regs)
            regs.orig_rax = 9
            regs.rdi = 0
            regs.rsi = 1024
            regs.rdx = mmap.PROT_READ | mmap.PROT_WRITE
            regs.r10 = mmap.MAP_ANONYMOUS | mmap.MAP_PRIVATE
            regs.r8 = -1
            regs.r9 = 0

            # resume and wait for syscall
            p.setregs(regs)
            p.syscall()
            p.waitSyscall()
            print('ok injected')

            print(hex(p.getInstrPointer()))

            # get mmap region
            addr = p.getregs().rax
            logging.info("%d mmap located at %X", p.pid, addr)

            # part 2
            p.setInstrPointer(pre - 2)
            p.syscall()
            p.waitSyscall()
            print('we can continue')

            backup.restore(regs)
            p.setregs(regs)

            self.injected.add(syscall.process.pid)
            syscall.process['mem'] = addr



            #p.setInstrPointer(before_syscall_addr)
            #p.syscall()

            #import struct
            #val = p.getregs().rax.to_bytes(8, byteorder='little')
            #print(struct.unpack("l", val))

            #from IPython import embed; embed()
