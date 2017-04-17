============================
Dynamic program modification
============================

Inject memory map
=================

.. code-block:: python

    with inject_memory(syscall.process, count) as mymemory:
        # do something with mymemory
        # when leaving this block, process state MUST be before syscall

Injection of syscall or code directly to process currently doesn't have any API, so look at some `examples <https://github.com/trnila/tracer/tree/master/examples/extensions>`_.


Change programs or arguments in execve
======================================
When traced application creates new process, you can change program and arguments:

Traced application counts number of users with shell */bin/sh*.

.. code-block:: bash

    $ tracer -n sh -c 'cat /etc/passwd | grep /bin/sh | wc -l'
    0

We can replace *cat /etc/passwd* with *sed* that replaces shells on fly.
Place following code snippet to your *tracer.conf.py* and run tracing again.

.. code-block:: python

    def replace_execve(execve):
        if execve.program == "/usr/bin/cat" and len(execve.arguments) == 2:
            execve.program = "/usr/bin/sed"
            execve.arguments = ["sed", "s/bash/sh/g", execve.arguments[1]]
            return execve

.. code-block:: bash

    $ tracer -e examples/extensions/replace_execve.py -n sh -c 'cat /etc/passwd | grep /bin/sh | wc -l'
    18

Tool replaced call *cat /etc/passwd* with *sed s/bash/sh/g /etc/passwd*.

It can be usefull if you want to add some flags to compilation when build system doesn't allow it.

Change opened files
===================
You can also replace path to opened files:

For example you can change */etc/hosts* with your own:

.. code-block:: bash

    $ tracer -e examples/extensions/replace_open_path.py -n --replace-path /etc/hosts:$(pwd)/fakehosts curl -v example.org
    * Rebuilt URL to: example.org/
    *   Trying 198.51.100.1...
