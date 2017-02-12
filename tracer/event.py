class Event:
    def __init__(self, process):
        self.process = process

    @property
    def tracer(self):
        return self.process.tracer


class Argument:
    def __init__(self, syscall, nth):
        self.syscall = syscall
        self.nth = nth

    @property
    def value(self):
        return self.syscall.backend.get_argument(self.syscall.process.pid, self.nth)

    @property
    def text(self):
        return self.syscall.process.read_cstring(self.value)
