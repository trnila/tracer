import logging

from tracer.extensions.extension import register_syscall, Extension


class HelloWorldExtension(Extension):
    def on_start(self, tracer):
        logging.error("Hello world extension initialized")

    @register_syscall("open")
    def handle_open(self, syscall):
        logging.error("Open called!")
