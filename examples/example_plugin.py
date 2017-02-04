import logging
from datetime import datetime

from tracer.syscalls.handler import *
from tracer.tracer import Tracer

t = Tracer()


class DemoExtension(Extension):
    def __init__(self):
        super().__init__()
        self.count = 0

    def on_start(self, tracer):
        logging.warning('counter initialized')

    def on_save(self, tracer):
        logging.warning("syscall open called %d times", self.count)

    @register_syscall('open')
    def open_handler(self, syscall):
        self.count += 1
        logging.warning('open triggered')


t.register_extension(DemoExtension())


@t.register_handler("open")
def myopen(syscall):
    logging.info("File %s opened", syscall.arguments[0].text)
    syscall.process.descriptors.get(syscall.result)['opened_time'] = datetime.now()


@t.register_handler("close")
class Test:
    def __call__(self, *args, **kwargs):
        logging.info('close called for descriptor %d', args[0].arguments[0].value)


t.main()
