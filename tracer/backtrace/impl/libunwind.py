import logging

import tracer.backtrace.libunwind
from tracer.backtrace.addr2line import Addr2line
from tracer.backtrace.backtrace import Frame


class Libunwind:
    def __init__(self):
        self.lib = tracer.backtrace.libunwind
        self.lib.init()
        self.symbols = {}

    def __del__(self):
        self.lib.destroy()

    def process_exited(self, pid):
        self.lib.destroy(pid)

    def create_backtrace(self, process):
        mappings = process.readMappings()
        import tracer.backtrace.libunwind

        try:
            backtrace_list = []
            for addr in self.lib.get_backtrace(process.pid):
                for mapping in mappings:
                    if addr in mapping and not mapping.pathname.startswith('['):
                        if mapping.pathname not in self.symbols:
                            self.symbols[mapping.pathname] = Addr2line(mapping.pathname)

                        addr = addr - mapping.start  # TODO: why relative address for code?

                        resolved = self.symbols[mapping.pathname].resolve(addr)
                        backtrace_list.append(Frame(addr, resolved if resolved else ""))
                        break
            return backtrace_list
        except tracer.backtrace.libunwind.error as err:
            logging.error("backtrace failed for pid %d: %s", process.pid, err)
