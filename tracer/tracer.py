import datetime
import logging
import os
import signal
import sys
from optparse import OptionParser

from ptrace.debugger import Application
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.error import PTRACE_ERRORS
from ptrace.error import writeError
from ptrace.func_call import FunctionCallOptions

import tracer
from tracer import fd
from tracer.Report import Report
from tracer.Report import UnknownFd
from tracer.backtracing.Libunwind import Libunwind
from tracer.backtracing.NullBacktracer import NullBacktracer
from tracer.syscalls.contents import read_or_write
from tracer.syscalls.core import handler_execve
from tracer.syscalls.handler import SyscallHandler
from tracer.syscalls.misc import mmap, kill, set_sock_opt

logging.getLogger().setLevel(logging.DEBUG)
try:
    import colorlog

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)s:%(name)s:%(message)s'))
    colorlog.getLogger().addHandler(handler)
except ImportError:
    # color log is just optional feature
    pass


class Tracer(Application):
    def __init__(self):
        Application.__init__(self)
        self.pids = {}
        self.syscall_options = FunctionCallOptions()
        self.debugger = PtraceDebugger()
        self.backtracer = NullBacktracer()
        self.parseOptions()
        self.data = Report(self.options.output)
        self.pipes = 0
        self.sockets = 0
        self.handler = SyscallHandler()
        self.handler.register(tracer.syscalls.core.HANDLERS)
        self.handler.register(tracer.syscalls.contents.HANDLERS)
        self.handler.register("mmap", mmap)
        self.handler.register("kill", kill)
        self.handler.register("setsockopt", set_sock_opt)

    def parseOptions(self):  # pylint: disable=C0103
        parser = OptionParser(usage="%prog [options] -- program [arg1 arg2 ...]")
        self.createCommonOptions(parser)
        parser.add_option('--output', '-o')
        parser.add_option('--trace-mmap', action="store_true", default=False)
        parser.add_option('--syscalls', '-s', help='print each syscall', action="store_true", default=False)
        parser.add_option('--print-data', '-d', help='print captured data to stdout', action="store_true",
                          default=False)
        parser.add_option('--backtrace', '-b', help='collect backtraces with libunwind', action="store_true",
                          default=False)

        self.createLogOptions(parser)

        self.options, self.program = parser.parse_args()

        if self.options.pid is None and not self.program:
            parser.print_help()
            sys.exit(1)

        if not self.options.output:
            self.options.output = '/tmp/tracer_%s_%s' % (
                self.program[0],
                datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S.%f")
            )

        if self.options.backtrace:
            self.backtracer = Libunwind()
            # self.backtracer = PythonPtraceBacktracer(self.debugger)

        self.options.enter = True

        self.processOptions()

    def displaySyscall(self, syscall):  # pylint: disable=C0103
        text = syscall.format()
        if self.options.syscalls:
            if syscall.result is not None:
                text = "%-40s = %s" % (text, syscall.result_text)
            prefix = ["[%s]" % syscall.process.pid]
            if prefix:
                text = ''.join(prefix) + ' ' + text
            logging.debug(text)

        self.handler.handle(self, syscall)

    def syscallTrace(self, process):  # pylint: disable=C0103
        # First query to break at next syscall
        self.prepareProcess(process)

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
                        if isinstance(capture.descriptor, fd.File):
                            for mmap_area in capture.descriptor.mmaps:
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
                self.processExecution(event)

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(self.syscall_options)

        if syscall and (syscall.result is not None):
            try:
                self.displaySyscall(syscall)
            except UnknownFd:
                logging.fatal("Unknown FD!")

        # Break at next syscall
        process.syscall()

    def processExited(self, event):  # pylint: disable=C0103
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") and (not self.options.enter) and state.syscall:
            self.displaySyscall(state.syscall)

        # Display exit message
        logging.info("*** %s ***", event)
        self.data.get_process(event.process.pid)['exitCode'] = event.exitcode

        self.backtracer.process_exited(event.process.pid)

    def prepareProcess(self, process):  # pylint: disable=C0103
        process.syscall()

    def newProcess(self, event):  # pylint: disable=C0103
        process = event.process
        logging.info("*** New process %s ***", process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread, process, self)

        self.prepareProcess(process)
        process.parent.syscall()

    def processExecution(self, event):  # pylint: disable=C0103
        process = event.process
        logging.info("*** Process %s execution ***", process.pid)
        process.syscall()

    def runDebugger(self):  # pylint: disable=C0103
        # Create debugger and traced process
        self.setupDebugger()
        process = self.createProcess()
        if not process:
            return
        self.data.get_process(process.pid).handle = process
        self.syscallTrace(process)

    def main(self):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()
        self.runDebugger()

        try:
            pass
            # self.runDebugger()
        except ProcessExit as event:
            self.processExited(event)
        except KeyboardInterrupt:
            logging.error("Interrupted.")
            self.debugger.quit()
        except PTRACE_ERRORS as err:
            writeError(logging.getLogger(), err, "Debugger error")
        self.debugger.quit()

        self.data.save()
        if self.options.print_data:
            self.data.save(sys.stdout)

        print("Report saved in %s" % self.options.output)

    def createChild(self, arguments, env=None):  # pylint: disable=C0103
        try:
            pid = Application.createChild(self, arguments, env)
        except Exception as e:
            print("Could not execute %s: %s" % (arguments, e))
            sys.exit(1)
        logging.debug("execve(%s, %s, [/* 40 vars */]) = %s", arguments[0], arguments, pid)

        proc = self.data.new_process(pid, 0, False, None, self)
        proc['executable'] = arguments[0]
        proc['arguments'] = arguments
        proc['env'] = dict(os.environ)

        proc.descriptors.open(fd.File(0, "stdin"))
        proc.descriptors.open(fd.File(1, "stdout"))
        proc.descriptors.open(fd.File(2, "stderr"))
        return pid

    def handle_sigterm(self, signum, frame):
        self.debugger.quit()

    def register_handler(self, syscall):
        def decorated(handler):
            self.handler.register(syscall, handler)

        return decorated
