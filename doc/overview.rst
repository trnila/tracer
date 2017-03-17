========
Overview
========

Tracer is tool for collecting data from running applications.
Collected data are written to JSON file at end of tracing.
Huge data like captures above descriptors or regions are placed in files.
Tracer currently collects following data:

* process

  * hiearchy
  * parent process
  * program executable and arguments
  * list of all switched working directories
  * environment variables at start of the process
  * exit code
  * thread or process
  * mmaped regions

    * address
    * size
    * region protection (currently at mmap call) 
    * flags
    * descriptor for non-anonymous mmaps
    * experimental track of non-anonymous region pages in memory
    * mmap memory content capture
  * reads and writes in descriptors
    
    * type (file, pipe, socket)
    * socket addresses for both sides
    * backtrace of descriptor creation
    * process who opened descriptor (could be easier to find out who did not set CLOEXEC)
    * operations

        * backtrace where data was read or written
        * size of data
        * seeks?
    * written/read content

Traced processes are inspected by ptrace system call (same as strace is using) so there is some overhead.
Collected data can be visualized with  `tracer-gui <https://github.com/trnila/tracer-gui>`_

This tool is using `python-ptrace <https://github.com/haypo/python-ptrace>`_ library for communication with ptrace.
