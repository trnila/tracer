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


class Socket(Descriptor):
    def __init__(self, fd):
        super().__init__(fd)
        self.label = "socket"
        self.addr = None
        self.port = None
        self.family = None

    def getLabel(self):
        if self.port is not None:
            return "%s:%s" % (self.addr, self.port)
        return self.addr
