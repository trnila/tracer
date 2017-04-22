=========
Backtrace
=========
Some events can also generate backtraces (or in another words stack traces).
Backtraces can be usefull when you want to know where in code descriptor was open or data was written.

Currently only C, C++ programs are supported with available debug informations, ie compiled with ``-g`` parameter.
Then you can invoke tracing with option ``--backtrace``.
But keep in mind, that tracing could be a bit slower.
