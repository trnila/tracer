class NullBacktracer:
    def create_backtrace(self, process):
        return []

    def process_exited(self, pid):
        pass