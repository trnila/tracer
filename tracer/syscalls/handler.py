from tracer.fd import Syscall


def register_syscall(a):
    def h(fn):
        fn._syscalls = a
        return fn

    return h


class Event:
    def __init__(self, process):
        self.process = process

    @property
    def tracer(self):
        return self.process.tracer


class PluginMount(type):
    def __init__(cls, name, bases, attrs, what):
        if not hasattr(cls, 'plugins'):
            # Called when the metaclass is first instantiated
            cls.plugins = []
        else:
            # Called when a plugin class is imported
            cls.register_plugin(cls)

    def register_plugin(cls, plugin):
        """Add the plugin to the plugin list and perform any registration logic"""

        # create a plugin instance and store it
        # optionally you could just store the plugin class and lazily instantiate
        instance = plugin()

        # save the plugin reference
        cls.plugins.append(instance)

        # apply plugin logic - in this case connect the plugin to blinker signals
        # this must be defined in the derived class
        instance.register_signals()


class Extension:
    __metaclass__ = PluginMount
    def on_start(self, tracer):
        pass

    def on_save(self, tracer):
        pass

    def on_process_created(self, event):
        pass

    def on_process_exit(self, process):
        pass


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
