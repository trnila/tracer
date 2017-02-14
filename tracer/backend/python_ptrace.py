import logging

from ptrace import PtraceError
from ptrace.debugger import DebuggerError
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
        self.stop_requested = False
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

        while not self.stop_requested:
            # No more process? Exit
            if not self.debugger:
                break

            # Wait until next syscall enter
            try:
                try:
                    # FIXME: better mechanism to stop debugger
                    # debugger._waitPid(..., blocking=False) may help
                    # actually debugger receives SIGTERM, terminates all remaining process
                    # then this method is unblocked and fails with KeyError
                    event = self.debugger.waitSyscall()
                except:
                    if self.stop_requested:
                        return
                    raise
                state = event.process.syscall_state
                syscall = state.event(FunctionCallOptions())

                self.syscalls[event.process.pid] = syscall

                yield SyscallEvent(event.process.pid, syscall.name)

                # FIXME:
                # when exit_group is called, it seems that thread is still monitored
                # in next event we area accessing pid that is not running anymore
                # so when exit_group occurs, remove all processes with same Tgid and detach from them
                if syscall.name == 'exit_group':  # result is None, never return!
                    def read_group(pid):
                        with open('/proc/%d/status' % pid) as f:
                            return int(
                                dict([(i, j.strip()) for i, j in [i.split(':', 1) for i in f.read().splitlines()]])[
                                    'Tgid'])

                    me = read_group(syscall.process.pid)
                    for process in self.debugger:
                        if read_group(process.pid) == me:
                            process.detach()
                            self.debugger.deleteProcess(pid=process.pid)
                            yield ProcessExited(process.pid, syscall.arguments[0].value)

                else:
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
            except DebuggerError:
                if self.stop_requested:
                    return
                raise


    def quit(self):
        self.stop_requested = True
        self.debugger.quit()
