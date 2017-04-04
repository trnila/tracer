import argparse
import logging

from tracer.extensions.extension import Extension, register_syscall


class StoreToDict(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not getattr(namespace, self.dest):
            setattr(namespace, self.dest, {})

        pair = values.split(':', 2)
        if len(pair) != 2:
            raise argparse.ArgumentError(self, "must have two values separated by colon, '{}' given".format(values))

        val = getattr(namespace, self.dest)
        val[pair[0]] = pair[1]


class ChangeOpenPath(Extension):
    """
    ChangeOpenPath replaces file in open syscalls
    Every path to replace have to be specified in parameter replace-path separated by colon, ie
    --replace-path requested:replaced

    Example:
    Print /etc/hosts instead of /etc/passwd in command cat /etc/passwd
    $ tracer -vvvvv -e ./examples/extensions/replace_open_path.py \
      --replace-path /etc/passwd:/etc/hosts \
      cat /etc/passwd
    """

    def create_options(self, parser):
        parser.add_argument(
            '--replace-path',
            action=StoreToDict,
            help='Replace path1 with path2 in open syscalls, --replace-path path1:path2',
            default={}
        )

    # TODO: openat
    @register_syscall("open", success_only=False)
    def change(self, syscall):
        paths = syscall.process.tracer.options.replace_path
        requested_path = syscall.arguments[0].text

        if syscall.name != "open" or syscall.result or requested_path not in paths:
            return

        new_path = paths[requested_path]
        logging.info("Replacing path %s with %s", requested_path, new_path)

        addr = syscall.process['mem']
        syscall.process.write_bytes(addr, new_path.encode('utf-8') + b'\0')

        p = syscall.process.tracer.backend.debugger[syscall.process.pid]
        regs = p.getregs()
        regs.rdi = addr
        p.setregs(regs)
