import logging
import os
import shutil
import signal
import sys
from argparse import Namespace, ArgumentParser

from tracer.backend.python_ptrace import PythonPtraceBackend, ProcessCreated, ProcessExited, SyscallEvent
from tracer.event import Event
from tracer.extensions.backtrace import Backtrace
from tracer.extensions.contents import ContentsExtension
from tracer.extensions.core import CoreExtension
from tracer.extensions.extension import Extension
from tracer.extensions.info import InfoExtension
from tracer.extensions.misc import MiscExtension
from tracer.extensions.mmap import MmapExtension
from tracer.extensions.report import ReportExtension
from tracer.extensions.shell import ShellExtension
from tracer.fd import Descriptor, Syscall


class Tracer:
    LOGGING_FORMAT = "==TRACER== %(levelname)s:%(name)s:%(message)s"

    def __init__(self):
        self.extensions = []
        self.backend = PythonPtraceBackend()
        self.options = Namespace()
        self.parse_options()
        self.data = None

    @staticmethod
    def create_core_parser():
        parser = ArgumentParser()
        parser.add_argument("--extension", "-e", help="path to extension file or directory to load",
                            action="append", default=[])
        parser.add_argument("-v", dest="logging_level", default=0, action="count")
        parser.add_argument('-p', dest="pid")
        parser.add_argument("program", nargs='?')
        parser.add_argument("arguments", nargs='*')

        return parser

    def parse_options(self):
        parser = self.create_core_parser()
        opts = parser.parse_known_args()[0]
        self.setup_logging(sys.stdout, opts.logging_level)

        # load extensions
        self.register_extension(ReportExtension())
        self.register_extension(CoreExtension())
        self.register_extension(ContentsExtension())
        self.register_extension(MiscExtension())
        self.register_extension(InfoExtension())
        self.register_extension(Backtrace())
        self.register_extension(MmapExtension())
        self.load_extensions([os.path.abspath(path) for path in opts.extension])
        self.register_extension(ShellExtension())

        # create options from all parsers
        for extension in self.extensions:
            extension.create_options(parser)

        # load full options
        self.options = parser.parse_args()
        self.options.fork = True
        self.options.trace_exec = True
        self.options.no_stdout = False
        self.options.enter = True

        # override from settings file
        self.options.__dict__.update(self.load_config())

        resolved = shutil.which(self.options.program)
        self.options.cmdline = [resolved] + self.options.arguments

        logging.debug("Current configuration: %s", self.options)

        if self.options.program and not resolved:
            logging.error("Could not resolve executable file %s", self.options.program)
            sys.exit(1)

        if self.options.pid is None and not self.options.program:
            print(self.options)
            parser.print_help()
            sys.exit(1)

    @staticmethod
    def load_config():
        options = {}
        for config_file in [os.path.expanduser('~/.tracerrc'), 'tracer.conf.py']:
            try:
                with open(config_file) as file:
                    loc = {}
                    exec(file.read(), {}, loc)
                    options.update(loc)
                    logging.info("Configuration file %s loaded", config_file)

            except FileNotFoundError:
                logging.warning("Configuration file %s not found", config_file)
        return options

    def setup_logging(self, fd, level):  # pylint: disable=C0103
        logger = logging.getLogger()
        logger.handlers.clear()
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

    def main(self):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        for extension in self.extensions:
            extension.on_start(self)

        self.backend.data = self.data
        self.create_child()

        for event in self.backend.start():
            if isinstance(event, ProcessCreated):
                self.data.new_process(
                    event.pid,
                    event.parent_pid,
                    event.is_thread,
                    self
                )

                for extension in self.extensions:
                    extension.on_process_created(self.data.get_process(event.pid))

            elif isinstance(event, ProcessExited):
                # Display exit message
                logging.info("*** %s ***", event)
                self.data.get_process(event.pid)['exitCode'] = event.exit_code

                evt = Event(self.data.get_process(event.pid))
                for extension in self.extensions:
                    extension.on_process_exit(evt)
            elif isinstance(event, SyscallEvent):
                proc = self.data.get_process(event.pid)
                syscall_obj = Syscall(proc, event.syscall_name, self.backend)

                logging.debug("syscall %s", syscall_obj)
                for extension in self.extensions:
                    try:
                        extension.on_syscall(syscall_obj)
                    except BaseException as e:
                        logging.exception("extension %s failed", extension)

            for extension in self.extensions:
                extension.on_tick(self)

        self.backend.quit()

        for extension in self.extensions:
            extension.on_save(self)

    def create_child(self):
        handle = self.backend.create_process(self.options.cmdline)
        proc = self.data.new_process(handle.pid, 0, False, self)
        proc['executable'] = self.options.cmdline[0]
        proc['arguments'] = self.options.cmdline
        proc['env'] = dict(os.environ)
        proc['cwd'] = [os.getcwd()]

        for extension in self.extensions:
            extension.on_process_created(proc)

        proc.descriptors.open(Descriptor.create_file(0, "stdin"))
        proc.descriptors.open(Descriptor.create_file(1, "stdout"))
        proc.descriptors.open(Descriptor.create_file(2, "stderr"))

    def handle_sigterm(self, signum, frame):
        self.backend.quit()

    def register_extension(self, extension):
        logging.info("Plugin %s registered", extension.__class__.__name__)
        self.extensions.append(extension)

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
                        globs = {}
                        exec(file.read(), globs)

                        for name, obj in globs.items():
                            if isinstance(obj, type):
                                if issubclass(obj, Extension):
                                    self.register_extension(obj())
                except Exception as e:
                    logging.exception("Could not load plugin %s", extension)
                    sys.exit(1)
