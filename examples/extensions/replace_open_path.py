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
    def create_options(self, parser):
        parser.add_argument(
            '--replace-path',
            action=StoreToDict,
            help='Replace path1 with path2 in open syscalls, --replace-path path1:path2',
            default={}
        )

    @register_syscall("open", success_only=False)
    def change(self, syscall):
        paths = syscall.process.tracer.options.replace_path
        requested_path = syscall.arguments[0].text

        if syscall.name != "open" or syscall.result or requested_path not in paths:
            return

        new_path = paths[requested_path]
        logging.info("Replacing path %s with %s", requested_path, new_path)

        addr = syscall.arguments[0].value
        syscall.process.write_bytes(addr, new_path.encode('utf-8') + b'\0')
