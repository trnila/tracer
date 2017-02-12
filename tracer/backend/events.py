class Evt:
    pass


class ProcessCreated(Evt):
    def __init__(self, pid, parent_pid, is_thread):
        self.pid = pid
        self.parent_pid = parent_pid
        self.is_thread = is_thread


class ProcessExited(Evt):
    def __init__(self, pid, exit_code):
        self.pid = pid
        self.exit_code = exit_code


class SyscallEvent(Evt):
    def __init__(self, pid, syscall_name):
        self.pid = pid
        self.syscall_name = syscall_name
