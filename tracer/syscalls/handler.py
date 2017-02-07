class Event:
    def __init__(self, process):
        self.process = process

    @property
    def tracer(self):
        return self.process.tracer