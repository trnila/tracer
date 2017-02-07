import logging


def register_syscall(a):
    def h(fn):
        fn._syscalls = a
        return fn

    return h


class Extension:
    def __init__(self):
        self._handlers = {}
        self._registered = False

    def create_options(self, parser):
        pass

    def on_start(self, tracer):
        pass

    def on_save(self, tracer):
        pass

    def on_process_created(self, event):
        pass

    def on_process_exit(self, process):
        pass

    def on_syscall(self, syscall):
        if not self._registered:
            self._registered = True
            self._register_decorated_handlers()

        if syscall.success and syscall.name in self._handlers:
            for handler in self._handlers[syscall.name]:
                handler(syscall)

    def register_handler(self, name, handler):
        if name not in self._handlers:
            self._handlers[name] = [handler]
        else:
            self._handlers[name].append(handler)

        logging.debug("Extension %s registered handler %s", self, name)

    def _register_decorated_handlers(self):
        for method in dir(self):
            syscalls = getattr(getattr(self, method), "_syscalls", None)
            if syscalls:
                if isinstance(syscalls, str):
                    syscalls = [syscalls]

                for syscall in syscalls:
                    self.register_handler(syscall, getattr(self, method))