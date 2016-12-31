import ctypes

from tracer.utils import get_root
from .addr2line import Addr2line
from .backtrace import Frame


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

    def get_backtrace(self, process):
        data = self.lib.get_backtrace(process.pid)
        casted = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))
        return casted


class Libunwind:
    def __init__(self):
        self.lib = CPTrace()
        self.symbols = {}

    def __del__(self):
        self.lib.destroy()

    def process_exited(self, pid):
        self.lib.destroy(pid)

    def create_backtrace(self, process):
        casted = self.lib.get_backtrace(process)

        mappings = process.readMappings()

        list = []
        i = 0
        while True:
            for mapping in mappings:
                if casted[i] in mapping and not mapping.pathname.startswith('['):
                    if mapping.pathname not in self.symbols:
                        self.symbols[mapping.pathname] = Addr2line(mapping.pathname)

                    addr = casted[i] - mapping.start # TODO: why relative address for code?

                    resolved = self.symbols[mapping.pathname].resolve(addr)
                    list.append(Frame(casted[i], resolved if resolved else ""))
                    break

            if casted[i] == 0:
                break
            i += 1

        return list