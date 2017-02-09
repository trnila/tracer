import logging
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.debugger.child import createChild
from ptrace.func_call import FunctionCallOptions

from tracer.event import Event
from tracer.fd import Syscall


class PythonPtraceBackend:
    def __init__(self):
        self.debugger = PtraceDebugger()
        self.root = None

        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()

    def attach_process(self, pid):
        self.root = self.debugger.addProcess(pid, is_attached=False)

    def create_process(self, arguments):
        pid = createChild(arguments, no_stdout=False)
        self.root = self.debugger.addProcess(pid, is_attached=True)
        return self.root

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

                if self.options.trace_mmap:
                    proc = self.data.get_process(event.process.pid)
                    for capture in proc['descriptors']:
                        if capture.descriptor.is_file and capture.descriptor['mmap']:
                            for mmap_area in capture.descriptor['mmap']:
                                mmap_area.check()

                self.syscall(event.process)
            except ProcessExit as event:
                self.processExited(event)
            except ProcessSignal as event:
                event.display()
                event.process.syscall(event.signum)
            except NewProcessEvent as event:
                self.newProcess(event)
            except ProcessExecution as event:
                logging.info("*** Process %s execution ***", event.process.pid)
                event.process.syscall()

        yield 'a'

    def processExited(self, event):  # pylint: disable=C0103
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") and state.syscall:
            # self.syscall(state.process) TODO:
            pass

        # Display exit message
        logging.info("*** %s ***", event)
        self.data.get_process(event.process.pid)['exitCode'] = event.exitcode

        evt = Event(self.data.get_process(event.process.pid))
        for extension in self.extensions:
            extension.on_process_exit(evt)

    def newProcess(self, event):  # pylint: disable=C0103
        process = event.process
        logging.info("*** New process %s ***", process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread, process, self)

        process.syscall()
        process.parent.syscall()

        for extension in self.extensions:
            extension.on_process_created(self.data.get_process(process.pid))

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(FunctionCallOptions())

        if syscall:
            proc = self.data.get_process(syscall.process.pid)
            syscall_obj = Syscall(proc, syscall)

            logging.debug("syscall %s", syscall_obj)
            for extension in self.extensions:
                try:
                    logging.debug("extension %s", extension)
                    extension.on_syscall(syscall_obj)
                except BaseException as e:
                    logging.exception("extension %s failed", extension)

        # Break at next syscall
        process.syscall()