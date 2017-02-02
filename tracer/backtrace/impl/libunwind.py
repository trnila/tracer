import ctypes

from tracer.utils import get_root
from tracer.backtrace.addr2line import Addr2line
from tracer.backtrace.backtrace import Frame


class CPTrace:
    def __init__(self):
        self.lib = ctypes.CDLL(get_root() + "backtrace/backtrace.so")
        self.lib.init()
        self.lib.get_backtrace.restype = ctypes.POINTER(ctypes.c_long)

    def destroy(self, pid=None):
        if pid is None:
            self.lib.destroy()
        else:
            self.lib.destroy_pid(pid)

    def get_backtrace(self, pid):
        data = self.lib.get_backtrace(pid)
        casted = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))

        addresses = []
        i = 0
        while casted[i] != 0:
            addresses.append(casted[i])
            i += 1

        return addresses


class Libunwind:
    def __init__(self):
        import backtrace
        self.lib = backtrace
        # self.lib = CPTrace()
        self.symbols = {}

    def __del__(self):
        self.lib.destroy()
        pass

    def process_exited(self, pid):
        self.lib.destroy(pid)

    def create_backtrace(self, process):
        mappings = process.readMappings()

        backtrace = []
        for addr in self.lib.get_backtrace(process.pid):
            for mapping in mappings:
                if addr in mapping and not mapping.pathname.startswith('['):
                    if mapping.pathname not in self.symbols:
                        self.symbols[mapping.pathname] = Addr2line(mapping.pathname)

                    addr = addr - mapping.start  # TODO: why relative address for code?

                    resolved = self.symbols[mapping.pathname].resolve(addr)
                    backtrace.append(Frame(addr, resolved if resolved else ""))
                    break

        return backtrace
