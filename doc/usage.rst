=====
Usage
=====
Add application you want to trace to arguments of trace program, eg::

    $ tracer /path/to/executable program arguments

You can also omit full path if program is in $PATH::

    $ tracer executable program arguments

Tracer configuration parameters must be added before executable name.
Following command creates report directly in /tmp/my-report directory. ::

    $ tracer -o /tmp/my-report executable

