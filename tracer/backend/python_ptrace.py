from ptrace.debugger import PtraceDebugger
from ptrace.debugger.child import createChild


class PythonPtraceBackend:
    def __init__(self):
        self.debugger = PtraceDebugger()
        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()

    def attach_process(self, pid):
        self.debugger.addProcess(pid, is_attached=False)

    def create_process(self, arguments):
        pid = createChild(arguments, no_stdout=False)
        return self.debugger.addProcess(pid, is_attached=True)
