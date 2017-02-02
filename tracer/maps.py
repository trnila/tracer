import mmap as MMAP
import os
import signal
import socket


class FlaggedDict:
    def __init__(self, flags):
        self.flags = flags

    def format(self, val):
        if not val:
            return ''

        opts = []
        for value, string in self.flags.items():
            if val & value:
                opts.append(string)

        return ' | '.join(opts)


class DictWithDefault:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.get(item)

    def get(self, item):
        if item in self.data:
            return self.data[item]
        return item


def create_map(module, start_with):
    return DictWithDefault(dict([(getattr(module, i), i) for i in dir(module) if i.startswith(start_with)]))


SIGNALS = create_map(signal, 'SIG')
MMAP_PROTS = FlaggedDict(create_map(MMAP, 'PROT_'))
MMAP_MAPS = FlaggedDict(create_map(MMAP, 'MAP'))
OPEN_MODES = FlaggedDict(create_map(os, 'O_'))
SOCKET_DOMAINS = create_map(socket, 'AF_')
SOCKET_TYPES = create_map(socket, 'SOCK_')
SOCKET_OPTS = create_map(socket, 'SO')
SOCKET_LEVEL = create_map(socket, 'SOL')
