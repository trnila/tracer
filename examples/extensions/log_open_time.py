import logging
from datetime import datetime

from tracer.extensions.extension import register_syscall, Extension


class LogOpenTimeExtension(Extension):
    def on_start(self, tracer):
        logging.info("LogOpenTime extension initialized")

    def on_save(self, tracer):
        logging.info("LogOpenTime extension finished")

    @register_syscall("open")
    def handle_open(self, syscall):
        descriptor = syscall.process.descriptors.get(syscall.result)
        descriptor['opened_at'] = datetime.now()
