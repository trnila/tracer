from .addr2line import Addr2line
from .backtrace import Frame


class PythonPtraceBacktracer:
    def __init__(self, debugger):
        self.query = None
        self.debugger = debugger

    def process_exited(self, pid):
        pass

    def create_backtrace(self, process):
        if not self.query:
            self.query = Addr2line(process['executable'])

        list = []

        for frame in self.debugger.dict[process['pid']].getBacktrace():
            resolved = self.query.resolve(frame.ip)
            list.append(Frame(frame.ip, resolved if resolved else ""))

        return list
