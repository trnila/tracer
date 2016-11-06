import ctypes

from tracer.utils import get_root
from .addr2line import Addr2line
from .backtrace import Frame


class Libunwind:
    def __init__(self):
        self.lib = ctypes.CDLL(get_root() + "backtrace/backtrace.so")
        self.lib.init()
        self.symbols = {}

    def __del__(self):
        self.lib.destroy()

    def process_exited(self, pid):
        self.lib.destroy_pid(pid)

    def create_backtrace(self, process):
        self.lib.get_backtrace.restype = ctypes.POINTER(ctypes.c_long)
        data = self.lib.get_backtrace(process.pid)
        casted = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))

        mappings = process.readMappings()

        list = []
        i = 0
        while True:
            for mapping in mappings:
                if casted[i] in mapping and not mapping.pathname.startswith('['):
                    if mapping.pathname not in self.symbols:
                        self.symbols[mapping.pathname] = Addr2line(mapping.pathname)

                    addr = casted[i] - mapping.start if ".so" in mapping.pathname else casted[i]

                    resolved = self.symbols[mapping.pathname].resolve(addr)
                    list.append(Frame(casted[i], resolved if resolved else ""))
                    break

            if casted[i] == 0:
                break
            i += 1

        return list