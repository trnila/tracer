class NullBacktracer:
    def create_backtrace(self, process):  # pylint: disable=unused-argument
        return []

    def process_exited(self, pid):
        pass
