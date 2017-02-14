class Backend:
    def attach_process(self, pid):
        raise NotImplementedError

    def create_process(self, arguments):
        raise NotImplementedError

    def get_argument(self, pid, num):
        """ get num'th argument from process with provided pid """
        raise NotImplementedError

    def get_syscall_result(self, pid):
        """ return value of last syscall in process """
        raise NotImplementedError

    def get_arguments_str(self, pid):
        """ return human readable description of arguments """
        return ""

    def read_cstring(self, pid, address):
        raise NotImplementedError

    def read_bytes(self, pid, address, size):
        raise NotImplementedError

    def create_backtrace(self, pid):
        raise NotImplementedError

    def start(self):
        """
        start monitoring process provided by attach_process or create_process
        function is generator that returns instances of tracer.backend.events.Evt
        """
        raise NotImplementedError

    def quit(self):
        raise NotImplementedError
