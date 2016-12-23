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
        for value, str in self.flags.items():
            if val & value:
                opts.append(str)

        return ' | '.join(opts)


def create_map(module, start_with):
    return dict([(getattr(module, i), i) for i in dir(module) if i.startswith(start_with)])


signals = create_map(signal, 'SIG')
mmap_prots = FlaggedDict(create_map(MMAP, 'PROT_'))
mmap_maps = FlaggedDict(create_map(MMAP, 'MAP'))
open_modes = FlaggedDict(create_map(os, 'O_'))
domains = create_map(socket, 'AF_')
socket_types = create_map(socket, 'SOCK_')
sockopts = create_map(socket, 'SO')
socklevel = create_map(socket, 'SOL')
