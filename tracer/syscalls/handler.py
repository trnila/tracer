from tracer.fd import Syscall


class SyscallHandler:
    def __init__(self):
        self.handlers = {}

    def register(self, syscalls, handler=None):
        if isinstance(syscalls, tuple):
            handler = syscalls[1]
            syscalls = syscalls[0]

        if handler is None:
            for syscall, callback in syscalls.items():
                self.register_single(syscall, callback)
        else:
            if isinstance(syscalls, str):
                syscalls = [syscalls]

            for syscall in syscalls:
                self.register_single(syscall, handler)

    def register_single(self, name, callback):
        if name not in self.handlers:
            self.handlers[name] = [callback]
        else:
            self.handlers[name].append(callback)

    def handle(self, tracer, syscall):
        if syscall.result >= 0 or syscall.result == -115:
            if syscall.name in self.handlers:
                proc = tracer.data.get_process(syscall.process.pid)

                for handler in self.handlers[syscall.name]:
                    handler(Syscall(proc, syscall))
