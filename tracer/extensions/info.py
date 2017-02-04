import platform
import socket
from datetime import datetime

from tracer.extensions.extension import Extension


class InfoExtension(Extension):
    def on_start(self, tracer):
        tracer.data['started'] = datetime.now()
        tracer.data['hostname'] = socket.getfqdn()
        tracer.data['arch'] = platform.machine()
        tracer.data['uname'] = " ".join(platform.uname())

    def on_save(self, tracer):
        tracer.data['finished'] = datetime.now()
