import ctypes

from tracer.utils import get_root
from .addr2line import Addr2line
from .backtrace import Frame


class Libunwind:
    def __init__(self):
        self.query = None
        self.lib = ctypes.CDLL(get_root() + "backtrace/backtrace.so")
        self.lib.init()

    def __del__(self):
        self.lib.destroy()

    def process_exited(self, pid):
        self.lib.destroy_pid(pid)

    def create_backtrace(self, process):
        self.lib.get_backtrace.restype = ctypes.POINTER(ctypes.c_long)
        data = self.lib.get_backtrace(process['pid'])
        casted = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))

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