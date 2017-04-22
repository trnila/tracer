===============
Shell extension
===============
This extension is usefull for stepping though system calls with descriptor information for example.
Extension can be enabled with ``--shell-enable``. Additionaly you can provide ``--shell-syscalls`` with comma separated names of syscalls to limit syscalls that you are interested in.
When tracer breaks before or after syscall, this extension drops you to the interactive python shell, where you can examine syscall, process, descriptors and more.
You can also write shell_filter function in configuration file to filter out unwanted syscalls. At any time you can set tracer.options.shell_filter = lambda syscall: syscall.name in ["close", "mmap"] to change filter function directly in interactive shell.

The following example shows shell extension with procfs(), that drops you to the */proc/pid/* directory where you can examine additional data about process.
::

    $ tracer --shell-enable --shell-syscalls brk,execve,close bash start.sh
    ...
    Press ctrl+d to continue with next syscall (not necessary from same process)

    syscall = brk(brk=0) = None
    process = <Process pid='14609' executable='/usr/bin/bash' arguments='['/usr/bin/bash', 'start.sh']'>
    tracer = <tracer.tracer.Tracer object at 0x7fe0c7f4da90>
    exit = Call to disable shell
    procfs = Call to drop into /proc/pid directory with $SHELL
    In [1]: procfs()
    [daniel@pc 14609]$ ls
    attr       cgroup      comm             cwd      fd      limits     mem        mountstats  numa_maps  oom_score_adj  root       smaps  statm    task
    autogroup  clear_refs  coredump_filter  environ  fdinfo  map_files  mountinfo  net         oom_adj    pagemap        sched      stack  status   timerslack_ns
    auxv       cmdline     cpuset           exe      io      maps       mounts     ns          oom_score  personality    schedstat  stat   syscall  wchan

When you call exit(), no further syscalls will break the program.

.. raw:: html

    <script type="text/javascript" src="https://asciinema.org/a/786udoxzbl8n5ocl2d4gnoy5g.js" id="asciicast-786udoxzbl8n5ocl2d4gnoy5g" async></script>
