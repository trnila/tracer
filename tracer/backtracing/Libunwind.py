import ctypes

from tracer.utils import get_root
from .addr2line import Addr2line
from .backtrace import Frame


class Libunwind:
    def __init__(self):
        self.lib = ctypes.CDLL(get_root() + "backtrace/backtrace.so")
        self.query = None

    def create_backtrace(self, process):
        self.lib.init.restype = ctypes.POINTER(ctypes.c_long)
        data = self.lib.init(process['pid'])
        casted = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))
        print(hex(casted[0]))

        if not self.query:
            self.query = Addr2line(process['executable'])

        list = []
        i = 0
        while True:
            resolved = self.query.resolve(casted[i])
            list.append(Frame(casted[i], resolved if resolved else ""))
            if casted[i] == 0:
                break
            i += 1

        return list