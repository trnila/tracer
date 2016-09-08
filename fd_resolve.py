import os


def resolve(pid, fd):
	return os.readlink("/proc/" + str(pid) + "/fd/" + str(fd))