import code
import os

from tracer.extensions.extension import Extension


class ExitCommand:
    def __init__(self, ext):
        self.extension = ext

    def __call__(self, *args, **kwargs):
        self.extension.enabled = False
        raise SystemExit

    def __str__(self):
        return "Call to disable shell"


class ProcFsShellCommand:
    def __init__(self, process):
        self.process = process

    def __call__(self, *args, **kwargs):
        cwd = os.getcwd()
        os.chdir("/proc/{}".format(self.process.pid))
        os.system(os.environ.get("SHELL", "/bin/bash"))
        os.chdir(cwd)

    def __str__(self):
        return "Call to drop into /proc/pid directory with $SHELL"


class CodeShell:
    def __init__(self):
        import code
        self.shell = code

    def run(self, banner, arguments):
        code.interact(banner=banner, local=arguments)


class IPythonShell:
    def __init__(self):
        from IPython import embed
        from traitlets.config import Config

        conf = Config()
        conf.TerminalInteractiveShell.confirm_exit = False

        self.config = conf
        self.shell = embed

    def run(self, banner, arguments):
        self.shell(config=self.config, banner1=banner, user_ns=arguments)


class ShellExtension(Extension):
    def __init__(self):
        super().__init__()
        self.enabled = True
        self.shell = None

    def create_options(self, parser):
        parser.add_argument('--shell-enable', help='Enable shell extension', action='store_true', default=False)
        parser.add_argument('--shell-syscalls', help='Whitelist syscall names in shell extension',
                            type=lambda x: x.split(','))

    def on_start(self, tracer):
        try:
            self.shell = IPythonShell()
        except ImportError:
            self.shell = CodeShell()

    def on_syscall(self, syscall):
        tracer = syscall.process.tracer
        whitelisted = tracer.options.shell_syscalls

        if not tracer.options.shell_enable or not self.enabled or (whitelisted and syscall.name not in whitelisted):
            return

        if 'shell_filter' in tracer.options and not tracer.options.shell_filter(syscall):
            return False

        local = {
            'syscall': syscall,
            'process': syscall.process,
            'tracer': tracer,
            'exit': ExitCommand(self),
            'procfs': ProcFsShellCommand(syscall.process),
            'backtrace': self._format_backtrace
        }

        banner = [
            "Press ctrl+d to continue with next syscall (not necessary from same process)",
            ""
        ]

        if tracer.options.backtrace:
            backtrace = self._format_backtrace(syscall.process.get_backtrace())
            banner.append("Backtrace")
            banner.append(backtrace)
            banner.append("")

        [banner.append("{} = {}".format(name, str(value))) for name, value in local.items()]

        try:
            self.shell.run("\n".join(banner), local)
        except SystemExit:
            # exit only this shell
            pass

    def _format_backtrace(self, backtrace):
        out = []

        for frame in backtrace:
            if frame.location:
                out.append(frame.location)
                out.append(self._format_codeblock(frame.location))

        return "\n".join(out)

    @staticmethod
    def _format_codeblock(location):
        file, num = location.split(':')
        num = int(num)

        out = []
        try:
            with open(file) as f:
                for i, line in enumerate(f):
                    if num - 5 < i < num + 5:
                        out.append("{prefix}{lineno:>5} {content}\033[0m".format(
                            prefix="\033[1m" if num == i else "",
                            lineno=i,
                            content=line.rstrip(),
                        ))

            return "\n".join(out)
        except FileNotFoundError:
            pass
