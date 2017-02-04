def register_syscall(a):
    def h(fn):
        fn._syscalls = a
        return fn

    return h


class Extension:
    def on_start(self, tracer):
        pass

    def on_save(self, tracer):
        pass

    def on_process_created(self, event):
        pass

    def on_process_exit(self, process):
        pass
