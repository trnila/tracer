import code

from tracer.extensions.extension import Extension


class ExitCommand:
    def __init__(self, ext):
        self.extension = ext

    def __call__(self, *args, **kwargs):
        self.extension.enabled = False
        raise SystemExit

    def __str__(self):
        return "Call to disable shell"


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

        try:
            self.shell = IPythonShell()
        except ModuleNotFoundError:
            self.shell = CodeShell()

    def on_syscall(self, syscall):
        tracer = syscall.process.tracer

        if not self.enabled:
            return

        local = {
            'syscall': syscall,
            'process': syscall.process,
            'tracer': tracer,
            'exit': ExitCommand(self)
        }

        banner = [
            "Press ctrl+d to continue with next syscall (not necessary from same process)",
            ""
        ]

        [banner.append("{} = {}".format(name, str(value))) for name, value in local.items()]

        try:
            self.shell.run("\n".join(banner), local)
        except SystemExit:
            # exit only this shell
            pass
