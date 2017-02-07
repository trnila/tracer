class Event:
    def __init__(self, process):
        self.process = process

    @property
    def tracer(self):
        return self.process.tracer


class Argument:
    def __init__(self, argument):
        self.argument = argument

    @property
    def value(self):
        return self.argument.value

    @property
    def text(self):
        return self.argument.text

    def __repr__(self):
        return "{}={}".format(
            self.argument.name,
            self.argument.text
        )