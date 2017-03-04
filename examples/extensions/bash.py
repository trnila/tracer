from tracer.extensions.extension import Extension
import logging
import struct

class BashExtension(Extension):
        addr_line_number = 0x6ceff4
        addr_the_printed_command = 0x6d0418

        def on_syscall(self, syscall):
            p = syscall.process

            line = struct.unpack("i", syscall.process.read_bytes(self.addr_line_number, 4))[0]
            cmd = syscall.process.read_cstring(struct.unpack("l", p.read_bytes(self.addr_the_printed_command, 8))[0])

            logging.error("LINE: %d command %s", line, cmd)
