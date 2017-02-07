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


class ShellExtension(Extension):
    def __init__(self):
        super().__init__()
        self.enabled = True

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
            code.interact(banner="\n".join(banner), local=local)
        except SystemExit:
            # exit only this shell
            pass
