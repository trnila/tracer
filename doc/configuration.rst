+++++++++++++
Configuration
+++++++++++++
Tracer can be configured with arguments and with configuration file.

List of possible arguments for all activated extensions is available by invoking following command

.. command-output:: tracer --help

After configuration parameters are parsed from arguments then they are merged with configurations stored in *~/.tracerrc* and *tracer.conf.py* stored in current working directory or file provided by *-c*.

Configuration file is plain python script that can set any option listed in tracer arguments and additionally can set some functions that influences tracing.`Example configuration files <https://github.com/trnila/tracer/tree/master/examples/settings>` shows some usage.

You can for example set *program*, *arguments* and *output* and invoke tracing by calling only `$ tracer`.

.. code-block:: python

    program = "./myapp"
    arguments = ["-x", "-y"]
    output = "./report"

Ignore files
============
Ignore some files by adding them to the *ignore_files*. Files can be also expressed by regexp.

.. code-block:: python

    ignore_files = [
        r'\/lib[^\/]+.so(\.[\d\-_]+)*$',  # .so shared libraries
        '/etc/passwd'
    ]

Ignore descriptors
==================
You can also write more complex resules. For each new descriptor *filter_out_descriptor* is called. 
The only argument is instance of class Descriptor. 
Your decision can be based on descriptor properties, process, etc.

.. code-block:: python

    # pass everything except pipes
    def filter_out_descriptor(descriptor):
        return descriptor.is_pipe
