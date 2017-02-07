import logging
import os
import signal
import sys

from ptrace.debugger import Application
from ptrace.debugger import NewProcessEvent
from ptrace.debugger import ProcessExecution
from ptrace.debugger import ProcessExit
from ptrace.debugger import ProcessSignal
from ptrace.debugger import PtraceDebugger
from ptrace.error import PTRACE_ERRORS
from ptrace.error import writeError
from ptrace.func_call import FunctionCallOptions

from tracer.arguments import create_core_parser
from tracer.backtrace.impl.null import NullBacktracer
from tracer.extensions.backtrace import Backtrace
from tracer.extensions.contents import ContentsExtension
from tracer.extensions.core import CoreExtension
from tracer.extensions.extension import Extension
from tracer.extensions.info import InfoExtension
from tracer.extensions.misc import MiscExtension
from tracer.extensions.report import ReportExtension
from tracer.fd import Descriptor
from tracer.report import UnknownFd
from tracer.syscalls.handler import SyscallHandler, Event


class Tracer(Application):
    LOGGING_FORMAT = "==TRACER== %(levelname)s:%(name)s:%(message)s"

    def __init__(self):
        Application.__init__(self)
        self.extensions = []
        self.debugger = PtraceDebugger()
        self.backtracer = NullBacktracer()
        self.handler = SyscallHandler()
        self.parseOptions()

    def parseOptions(self):  # pylint: disable=C0103
        parser = create_core_parser()
        opts = parser.parse_known_args()[0]
        self.setup_logging(sys.stdout, opts.logging_level)

        # load extensions
        self.register_extension(ReportExtension())
        self.register_extension(CoreExtension())
        self.register_extension(ContentsExtension())
        self.register_extension(MiscExtension())
        self.register_extension(InfoExtension())
        self.register_extension(Backtrace())
        self.load_extensions([os.path.abspath(path) for path in opts.extension])

        # create options from all parsers
        for extension in self.extensions:
            extension.create_options(parser)

        # load full options
        self.options = parser.parse_args()
        self.options.fork = True
        self.options.trace_exec = True
        self.options.no_stdout = False
        self.options.enter = True
        self.program = [self.options.program] + self.options.arguments

        if self.options.pid is None and not self.program:
            parser.print_help()
            sys.exit(1)

        self.processOptions()

    def setup_logging(self, fd, level):  # pylint: disable=C0103
        logger = logging.getLogger()
        logger.addHandler(logging.StreamHandler(fd))
        logger.setLevel(max(logging.ERROR - (level * 10), 1))
        try:
            import colorlog

            handler = logging.getLogger().handlers[0]
            handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s' + self.LOGGING_FORMAT))
            colorlog.getLogger().addHandler(handler)
        except ImportError:
            # color log is just optional feature
            logging.getLogger().handlers[0].setFormatter(logging.Formatter(self.LOGGING_FORMAT))

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
                self.processExecution(event)

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(FunctionCallOptions())

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

        evt = Event(self.data.get_process(event.process.pid))
        for extension in self.extensions:
            extension.on_process_exit(evt)

    def prepareProcess(self, process):  # pylint: disable=C0103
        process.syscall()

    def newProcess(self, event):  # pylint: disable=C0103
        process = event.process
        logging.info("*** New process %s ***", process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread, process, self)

        self.prepareProcess(process)
        process.parent.syscall()

        for extension in self.extensions:
            extension.on_process_created(self.data.get_process(process.pid))

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

        for extension in self.extensions:
            extension.on_start(self)

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

        for extension in self.extensions:
            extension.on_save(self)

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

        for extension in self.extensions:
            extension.on_process_created(proc)

        proc.descriptors.open(Descriptor.create_file(0, "stdin"))
        proc.descriptors.open(Descriptor.create_file(1, "stdout"))
        proc.descriptors.open(Descriptor.create_file(2, "stderr"))
        return pid

    def handle_sigterm(self, signum, frame):
        self.debugger.quit()

    def register_extension(self, extension):
        logging.info("Plugin %s registered", extension.__class__.__name__)
        self.extensions.append(extension)

        for method in dir(extension):
            syscalls = getattr(getattr(extension, method), "_syscalls", None)
            if syscalls:
                self.handler.register(syscalls, getattr(extension, method))

    def load_extensions(self, extensions):
        for extension in extensions:
            if os.path.isdir(extension):
                logging.debug("Looking for extension in %s", extension)
                for node in os.listdir(extension):
                    self.load_extensions([os.path.join(extension, node)])
            else:
                logging.debug("Loading plugin from %s", extension)
                try:
                    with open(extension) as file:
                        globs = {
                            "logging": logging
                        }
                        exec(file.read(), globs)

                        for name, obj in globs.items():
                            if isinstance(obj, type):
                                if issubclass(obj, Extension):
                                    self.register_extension(obj())
                except Exception as e:
                    logging.fatal("Could not load plugin %s: %s", extension, e)
                    sys.exit(1)
