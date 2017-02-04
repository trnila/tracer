import logging
from datetime import datetime

from tracer.tracer import Tracer

t = Tracer()


@t.register_handler("open")
def myopen(syscall):
    logging.info("File %s opened", syscall.arguments[0].text)
    syscall.process.descriptors.get(syscall.result)['opened_time'] = datetime.now()


@t.register_handler("close")
class Test:
    def __call__(self, *args, **kwargs):
        logging.info('close called for descriptor %d', args[0].arguments[0].value)

t.main()
