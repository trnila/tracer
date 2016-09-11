import os
import platform


def resolve(pid, fd):
    if 'bsd' in platform.system().lower():
        # TODO: use procstat
        return str(fd)

    return os.readlink("/proc/" + str(pid) + "/fd/" + str(fd))
