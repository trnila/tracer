import logging


def register_syscall(a, success_only=True):
    def h(fn):
        fn._syscalls = a
        fn._success_only = success_only
        return fn

    return h


class Extension:
    def __init__(self):
        self._handlers = {}  # (handler, success_only)
        self._registered = False

    def create_options(self, parser):
        pass

    def on_start(self, tracer):
        pass

    def on_save(self, tracer):
        pass

    def on_process_created(self, process):
        pass

    def on_process_exit(self, process):
        pass

    def on_syscall(self, syscall):
        if not self._registered:
            self._registered = True
            self._register_decorated_handlers()

        for handler, success_only in self._handlers.get(syscall.name, []):
            if success_only and not syscall.success:
                continue
            handler(syscall)

    def register_handler(self, name, handler, success_only=True):
        if name not in self._handlers:
            self._handlers[name] = []
        self._handlers[name].append((handler, success_only))

        logging.debug("Extension %s registered handler %s", self, name)

    def _register_decorated_handlers(self):
        for method in dir(self):
            method_obj = getattr(self, method)

            syscalls = getattr(method_obj, "_syscalls", None)
            if syscalls:
                if isinstance(syscalls, str):
                    syscalls = [syscalls]

                for syscall in syscalls:
                    self.register_handler(
                        syscall,
                        method_obj,
                        method_obj._success_only
                    )

    def on_tick(self, tracer):
        pass
