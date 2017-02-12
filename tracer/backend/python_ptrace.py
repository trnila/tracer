import logging

from ptrace import PtraceError
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.debugger.child import createChild
from ptrace.func_call import FunctionCallOptions

from tracer.backend.backend import Backend
from tracer.backend.events import SyscallEvent, ProcessExited, ProcessCreated
from tracer.backtrace.impl.null import NullBacktracer


class PythonPtraceBackend(Backend):
    def __init__(self):
        self.debugger = PtraceDebugger()
        self.root = None
        self.syscalls = {}
        self.backtracer = NullBacktracer()

        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()

    def attach_process(self, pid):
        self.root = self.debugger.addProcess(pid, is_attached=False)

    def create_process(self, arguments):
        pid = createChild(arguments, no_stdout=False)
        self.root = self.debugger.addProcess(pid, is_attached=True)
        return self.root

    def get_argument(self, pid, num):
        return self.syscalls[pid].arguments[num].value

    def get_syscall_result(self, pid):
        if self.syscalls[pid]:
            return self.syscalls[pid].result

        return None

    def read_cstring(self, pid, address):
        try:
            return self.debugger[pid].readCString(address, 255)[0].decode('utf-8')
        except PtraceError as e:
            # TODO: ptrace's PREFORMAT_ARGUMENTS, why they are lost?
            for arg in self.syscalls[pid].arguments:
                if arg.value == address:
                    return arg.text
            raise e

    def read_bytes(self, pid, address, size):
        return self.debugger[pid].readBytes(address, size)

    def create_backtrace(self, pid):
        return self.backtracer.create_backtrace(self.debugger[pid])

    def start(self):
        # First query to break at next syscall
        self.root.syscall()

        while True:
            # No more process? Exit
            if not self.debugger:
                break

            # Wait until next syscall enter
            try:
                event = self.debugger.waitSyscall()
                state = event.process.syscall_state
                syscall = state.event(FunctionCallOptions())

                self.syscalls[event.process.pid] = syscall

                yield SyscallEvent(event.process.pid, syscall.name)

                # Break at next syscall
                event.process.syscall()
            except ProcessExit as event:
                # Display syscall which has not exited
                state = event.process.syscall_state
                if (state.next_event == "exit") and state.syscall:
                    # self.syscall(state.process) TODO:
                    pass

                yield ProcessExited(event.process.pid, event.exitcode)
            except ProcessSignal as event:
                event.display()
                event.process.syscall(event.signum)
            except NewProcessEvent as event:
                process = event.process
                logging.info("*** New process %s ***", process.pid)

                yield ProcessCreated(
                    pid=process.pid,
                    parent_pid=process.parent.pid,
                    is_thread=process.is_thread
                )

                process.syscall()
                process.parent.syscall()
            except ProcessExecution as event:
                logging.info("*** Process %s execution ***", event.process.pid)
                event.process.syscall()

    def quit(self):
        self.debugger.quit()