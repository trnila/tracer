from tracer.tracer import Tracer
from datetime import datetime
import logging

t = Tracer()


@t.register_handler("open")
def myopen(syscall):
    logging.info("File %s opened", syscall.arguments[0].text)
    syscall.process.descriptors.get(syscall.result)['opened_time'] = datetime.now()

t.main()
