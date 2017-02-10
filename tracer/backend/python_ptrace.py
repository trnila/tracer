import logging

from ptrace import PtraceError
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.debugger.child import createChild
from ptrace.func_call import FunctionCallOptions


class Evt:
    PROCESS_CREATED = 'create'
    PROCESS_EXITED = 'exit'
    SYSCALL = 'syscall'


class ProcessCreated(Evt):
    def __init__(self, process):
        self.process = process


class ProcessExited(Evt):
    def __init__(self, pid, exit_code):
        self.pid = pid
        self.exit_code = exit_code


class SyscallEvent(Evt):
    def __init__(self, pid, syscall_name):
        self.pid = pid
        self.syscall_name = syscall_name




class PythonPtraceBackend:
    def __init__(self):
        self.debugger = PtraceDebugger()
        self.root = None
        self.syscalls = {}

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

                if self.options.trace_mmap:
                    proc = self.data.get_process(event.process.pid)
                    for capture in proc['descriptors']:
                        if capture.descriptor.is_file and capture.descriptor['mmap']:
                            for mmap_area in capture.descriptor['mmap']:
                                mmap_area.check()

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

                yield ProcessCreated(event.process)

                process.syscall()
                process.parent.syscall()
            except ProcessExecution as event:
                logging.info("*** Process %s execution ***", event.process.pid)
                event.process.syscall()
