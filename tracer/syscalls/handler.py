class SyscallHandler:
    def __init__(self):
        self.handlers = {}

    def register(self, syscalls, handler):
        if isinstance(syscalls, str):
            syscalls = [syscalls]

        for syscall in syscalls:
            self.handlers[syscall] = handler

    def handle(self, tracer, syscall):
        if syscall.result >= 0 or syscall.result == -115:
            if syscall.name in self.handlers:
                proc = tracer.data.get_process(syscall.process.pid)
                self.handlers[syscall.name](proc, syscall, tracer)