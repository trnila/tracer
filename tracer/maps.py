import mmap as MMAP
import os
import signal
import socket
import stat


class FlaggedDict:
    def __init__(self, flags, postprocess=lambda x: x):
        self.flags = flags
        self.postprocess = postprocess

    def format(self, val):
        opts = []
        for value, string in self.flags.items():
            if val & value:
                opts.append(string)

        return self.postprocess(opts)

    def __repr__(self):
        return self.flags.__repr__()


class DictWithDefault:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.get(item)

    def items(self):
        return self.data.items()

    def get(self, item):
        if item in self.data:
            return self.data[item]
        return item

    def __repr__(self):
        content = "\n\t".join([
                                  "{}={}".format(key, value)
                                  for key, value in self.items()
                                  ])

        return "FlaggedDict<\n\t{}\n>".format(content)


def create_map(module, start_with):
    values = {
        getattr(module, i): i for i in dir(module)
        if i.startswith(start_with) and isinstance(getattr(module, i), int)
        }
    return DictWithDefault(values)


SIGNALS = create_map(signal, 'SIG')
MMAP_PROTS = FlaggedDict(create_map(MMAP, 'PROT_'))
MMAP_MAPS = FlaggedDict(create_map(MMAP, 'MAP'))
SOCKET_DOMAINS = create_map(socket, 'AF_')
SOCKET_TYPES = create_map(socket, 'SOCK_')
SOCKET_OPTS = create_map(socket, 'SO')
SOCKET_LEVEL = create_map(socket, 'SOL')


def _open_flags_postprocess(items):
    if 'O_RDRW' not in items and 'O_WRONLY' not in items:
        items.append('O_RDONLY')
    return items


OPEN_FLAGS = FlaggedDict(create_map(os, 'O_'), _open_flags_postprocess)
OPEN_MODES = FlaggedDict(create_map(stat, 'S_'))
