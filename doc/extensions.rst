=========
Extension
=========
Extensions could be inserted to tracer to collect user-defined additional data. 
When you run `$ tracer -e my_extension.py ls`, the extension will be enabled.
Each extension must subclass from Extension class and optionally implement some functions:

create_options(parser)
    description can register some parameters to command line arguments
on_start(tracer)
    called when tracing started
on_save(tracer)
    called before JSON report is saved to file at end of tracing
on_process_created(process)
    called when new process created
on_process_exit(process)
    called when process exited correctly or crashed
on_syscall(syscall)
    called before or after each syscall

Extension can also define function decorated with *@register_syscall* that will handle syscall.
Argument of this decorator could be single string of syscall name or list. Additionaly you can set *success_only=False* to handle failed and not-yet-processed syscalls.

For more information how to create own extension look at `basic extensions <https://github.com/trnila/tracer/tree/master/tracer/extensions>`_.


.. code-block:: python

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
