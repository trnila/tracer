class Descriptor:
    def __init__(self, fd):
        self.fd = fd

    def getLabel(self):
        return ""

    def getId(self):
        return None


class Pipe(Descriptor):
    def __init__(self, fd):
        super().__init__(fd)

    def getLabel(self):
        return "pipe"


class FileDescriptor(Descriptor):
    def __init__(self, fd, path):
        super().__init__(fd)
        self.path = path
        self.seeks = []

    def getLabel(self):
        return self.path


class UnixSocket(Descriptor):
    def __init__(self, fd, path):
        super().__init__(fd)
        self.path = path

    def getLabel(self):
        return "unix"


class NetworkSocket(Descriptor):
    def __init__(self, fd):
        super().__init__(fd)

    def getLabel(self):
        return "tcp socket"
