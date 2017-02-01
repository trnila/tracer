#!/usr/bin/env python
import datetime
import logging
import os
import signal
import sys
from optparse import OptionParser
from sys import exit

from ptrace.debugger import Application
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.error import PTRACE_ERRORS
from ptrace.error import writeError
from ptrace.func_call import FunctionCallOptions

from tracer import fd
from tracer.Report import Report
from tracer.Report import UnknownFd
from tracer.backtracing.Libunwind import Libunwind
from tracer.backtracing.NullBacktracer import NullBacktracer
from tracer.syscalls.contents import ReadOrWrite
from tracer.syscalls.core import Execve, Open, Socket, Pipe, Bind, ConnectLike, Dup2, Close, DupLike
from tracer.syscalls.handler import SyscallHandler
from tracer.syscalls.misc import Mmap, Kill, SetSockOpt

logging.getLogger().setLevel(logging.DEBUG)
try:
    import colorlog

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)s:%(name)s:%(message)s'))
    colorlog.getLogger().addHandler(handler)
except:
    # color log is just optional feature
    pass


class Tracer(Application):
    def __init__(self):
        Application.__init__(self)
        self.debugger = PtraceDebugger()
        self.backtracer = NullBacktracer()
        self.parseOptions()
        self.data = Report(self.options.output)
        self.pipes = 0
        self.sockets = 0
        self.handler = SyscallHandler()
        self.handler.register("open", Open)
        self.handler.register("socket", Socket)
        self.handler.register("pipe", Pipe)
        self.handler.register("bind", Bind)
        self.handler.register(["connect", "accept", "syscall<288>"], ConnectLike)
        self.handler.register("dup2", Dup2)
        self.handler.register("close", Close)
        self.handler.register("mmap", Mmap)
        self.handler.register(["dup", "fcntl"], DupLike) # elif syscall.name == 'dup' or (syscall.name == 'fcntl' and syscall.arguments[1].value == 0):  # F_DUPFD = 0
        self.handler.register("kill", Kill)
        self.handler.register(["read", "write", "sendmsg", "recvmsg", "sendto", "recvfrom"], ReadOrWrite)
        self.handler.register("execve", Execve)
        self.handler.register("setsockopt", SetSockOpt)

    def parseOptions(self):
        parser = OptionParser(usage="%prog [options] -- program [arg1 arg2 ...]")
        self.createCommonOptions(parser)
        parser.add_option('--output', '-o')
        parser.add_option('--trace-mmap', action="store_true", default=False)
        parser.add_option('--syscalls', '-s', help='print each syscall', action="store_true", default=False)
        parser.add_option('--print-data', '-d', help='print captured data to stdout', action="store_true", default=False)
        parser.add_option('--backtrace', '-b', help='collect backtraces with libunwind', action="store_true", default=False)

        self.createLogOptions(parser)

        self.options, self.program = parser.parse_args()

        if self.options.pid is None and not self.program:
            parser.print_help()
            exit(1)

        if not self.options.output:
            self.options.output = '/tmp/tracer_%s_%s' % (
                self.program[0],
                datetime.datetime.now().strftime("%d-%m-%Y_%H:%M:%S.%f")
            )

        if self.options.backtrace:
            self.backtracer = Libunwind()
            #self.backtracer = PythonPtraceBacktracer(self.debugger)

        self.options.enter = True

        self.processOptions()

    def displaySyscall(self, syscall):
        text = syscall.format()
        if self.options.syscalls:
            if syscall.result is not None:
                text = "%-40s = %s" % (text, syscall.result_text)
            prefix = ["[%s]" % syscall.process.pid]
            if prefix:
                text = ''.join(prefix) + ' ' + text
            logging.debug(text)

        self.handler.handle(self, syscall)

    def syscallTrace(self, process):
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
                            for mmap in capture.descriptor.mmaps:
                                mmap.check()

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

    def processExited(self, event):
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") and (not self.options.enter) and state.syscall:
            self.displaySyscall(state.syscall)

        # Display exit message
        logging.info("*** %s ***" % event)
        self.data.get_process(event.process.pid)['exitCode'] = event.exitcode

        self.backtracer.process_exited(event.process.pid)

    def prepareProcess(self, process):
        process.syscall()

    def newProcess(self, event):
        process = event.process
        logging.info("*** New process %s ***" % process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread, process, self)

        self.prepareProcess(process)
        process.parent.syscall()

    def processExecution(self, event):
        process = event.process
        logging.info("*** Process %s execution ***" % process.pid)
        process.syscall()

    def runDebugger(self):
        # Create debugger and traced process
        self.setupDebugger()
        process = self.createProcess()
        if not process:
            return
        self.data.get_process(process.pid).handle = process

        self.syscall_options = FunctionCallOptions()

        self.syscallTrace(process)

    def main(self):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        self.pids = {}
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

    def createChild(self, program, **kwargs):
        try:
            pid = Application.createChild(self, program)
        except Exception as e:
            print("Could not execute %s: %s" % (program, e))
            sys.exit(1)
        logging.debug("execve(%s, %s, [/* 40 vars */]) = %s" % (program[0], program, pid))

        proc = self.data.new_process(pid, 0, False, None, self)
        proc['executable'] = program[0]
        proc['arguments'] = program
        proc['env'] = dict(os.environ)

        proc.descriptors.open(fd.File(0, "stdin"))
        proc.descriptors.open(fd.File(1, "stdout"))
        proc.descriptors.open(fd.File(2, "stderr"))
        return pid

    def handle_sigterm(self, signum, frame):
        self.debugger.quit()
