# tracer [![Build Status](https://travis-ci.org/trnila/tracer.svg?branch=master)](https://travis-ci.org/trnila/tracer)
## Dependencies
- at least Python 3.2
- libunwind
- addr2line


## Installation
To install development version from branch master run:
```sh
pip3 install git+https://github.com/trnila/tracer.git
```

Optional dependencies are *colorlog* and *ipython* so if you want to have better interface install them:
```sh
pip3 install colorlog ipython
```

### Installation with virtualenv on Ubuntu 16.10
```
sudo apt-get install python-virtualenv python3-dev git libunwind8-dev python3-pip
virtualenv -p python3 venv3
source venv3/bin/activate
pip3 install git+https://github.com/trnila/tracer.git
pip3 install colorlog ipython # optional
```

## Usage
```sh
tracer -- sh -c "curl httpbin.com/headers ; cat /etc/passwd | tr a-z A-Z | tac" 
```

For more information about options run
```sh
tracer -h
```

## Examples
If you clone this repository somewhere, you can run interesting examples though helper script `./examples/run`,
but it requires `tracer` and [`tracergui`](https://github.com/trnila/tracer-gui) in your *PATH*. 
It can be achieved by installing both applications with *
*.  

## Configuration
Configuration options from command line arguments are merged with configuration file *~/.tracerrc* and with
file *tracer.conf.py* in current working directory.
Syntax of configuration file is Python and all defined variables are merged with configuration.

Example:
```python
output = '/tmp/my-reports'
program = "ls"
arguments = ['-l', '/']


def shell_filter(syscall):
    return syscall.success and syscall.name == 'open'
```
So from now, you can just run `tracer` to trace program `ls`.

### Filter unwanted descriptors
Filtering currently happens at the time of descriptor creation.
Place regexps of paths to configuration file, eg:
```python
ignore_files = [
    r'\/lib[^\/]+.so(\.[\d\-_]+)*$',  # ignore .so shared libraries
    r'cache'
]
```

There is also support for user-defined filter function in configuration file:
```python
# pass everything except pipes
def filter_out_descriptor(descriptor):
    return descriptor.is_pipe
```

## User defined extensions
Create somewhere python file with this class:
```python
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
```
When you run `tracer -e my_extension.py ls`, this extension will be enabled.
For more information how to create own extension look at [basic extensions](tracer/extensions).

## Shell extension
When tracer breaks before or after syscall, this extension drops you to the interactive python shell,
where you can examine syscall, process, descriptors and more. 

```sh
tracer --shell-enable --shell-syscalls open,read,write ls
```

You can also write *shell_filter* function in configuration file to filter out unwanted syscalls.
At any time you can set `tracer.options.shell_filter = lambda syscall: syscall.name in ["close", "mmap"]`
to change filter function directly in interactive shell.

## Development
```sh
git clone https://github.com/trnila/tracer
cd tracer
python setup.py develop
```

### Tests
Run `python -m unittest` or `pytest` if you have pytest installed.
