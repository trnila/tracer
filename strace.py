#!/usr/bin/env python
import ipaddress
import json
import os
import random
import re
import socket
import string
from logging import getLogger, error
from optparse import OptionParser
from struct import unpack
from sys import stderr, exit

from ptrace.cpu_info import CPU_WORD_SIZE
from ptrace.debugger import (PtraceDebugger, Application,
    ProcessExit, ProcessSignal, NewProcessEvent, ProcessExecution)
from ptrace.error import PTRACE_ERRORS, writeError
from ptrace.func_call import FunctionCallOptions
from ptrace.syscall import (SYSCALL_NAMES, SYSCALL_PROTOTYPES,
                            FILENAME_ARGUMENTS)

import fd
import utils
from Report import Report
from TracedData import TracedData
from fd_resolve import resolve
from json_encode import AppJSONEncoder


class SyscallTracer(Application):
    def __init__(self):
        Application.__init__(self)

        # Parse self.options
        self.parseOptions()
        self.data = Report(self.options.output)
        self.pipes = 0
        self.sockets = 0

    def parseOptions(self):
        parser = OptionParser(usage="%prog [options] -- program [arg1 arg2 ...]")
        self.createCommonOptions(parser)
        parser.add_option("--ignore-regex", help="Regex used to filter syscall names (eg. --ignore='^(gettimeofday|futex|f?stat)')",
            type="str")
        parser.add_option("--syscalls", '-e', help="Comma separated list of shown system calls (other will be skipped)",
            type="str", default=None)
        parser.add_option("--filename", help="Show only syscall using filename",
            action="store_true", default=False)

        parser.add_option('--output', '-o')

        self.createLogOptions(parser)

        self.options, self.program = parser.parse_args()

        if not self.options.output:
            self.options.output = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

        self.options.enter = True

        if self.options.pid is None and not self.program:
            parser.print_help()
            exit(1)

        # Create "only" filter
        only = set()
        if self.options.syscalls:
            # split by "," and remove spaces
            for item in self.options.syscalls.split(","):
                item = item.strip()
                if not item or item in only:
                    continue
                ok = True
                valid_names = list(SYSCALL_NAMES.values())
                for name in only:
                    if name not in valid_names:
                        print("ERROR: unknow syscall %r" % name, file=stderr)
                        ok = False
                if not ok:
                    print(file=stderr)
                    print("Use --list-syscalls options to get system calls list", file=stderr)
                    exit(1)
                # remove duplicates
                only.add(item)
        if self.options.filename:
            for syscall, format in SYSCALL_PROTOTYPES.items():
                restype, arguments = format
                if any(argname in FILENAME_ARGUMENTS for argtype, argname in arguments):
                    only.add(syscall)
        self.only = only
        if self.options.ignore_regex:
            try:
                self.ignore_regex = re.compile(self.options.ignore_regex)
            except Exception as err:
                print("Invalid regular expression! %s" % err)
                print("(regex: %r)" % self.options.ignore_regex)
                exit(1)
        else:
            self.ignore_regex = None

        self.processOptions()

        os.makedirs(self.options.output, exist_ok=True)

    def ignoreSyscall(self, syscall):
        name = syscall.name
        if self.only and (name not in self.only):
            return True
        if self.ignore_regex and self.ignore_regex.match(name):
            return True
        return False

    def displaySyscall(self, syscall):
        name = syscall.name
        text = syscall.format()
        if syscall.result is not None:
            text = "%-40s = %s" % (text, syscall.result_text)
        prefix = []
        prefix.append("[%s]" % syscall.process.pid)
        if prefix:
            text = ''.join(prefix) + ' ' + text
        error(text)

        proc = self.data.get_process(syscall.process.pid)

        if syscall.result >= 0 or syscall.result == -115: # EINPROGRESS
            if syscall.name == 'open':
                proc.descriptors.open(fd.File(self.data, syscall.result, syscall.arguments[0].text))
            elif syscall.name == 'socket':
                descriptor = fd.Socket(self.data, syscall.result, self.sockets)
                descriptor.family = syscall.arguments[0].value
                proc.descriptors.open(descriptor)
                self.sockets += 1
            elif syscall.name == 'pipe':
                pipe = syscall.process.readBytes(syscall.arguments[0].value, 8)
                fd1, fd2 = unpack("ii", pipe)
                proc.descriptors.open(fd.Pipe(self.data, fd1, self.pipes))
                proc.descriptors.open(fd.Pipe(self.data, fd2, self.pipes))
                self.pipes += 1
            elif syscall.name == 'bind':
                descriptor = proc.descriptors.get(syscall.arguments[0].value)
                bytes = syscall.process.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
                descriptor.local = utils.parse_addr(bytes)
            elif syscall.name in ['connect', 'accept', 'syscall<288>']:
                # struct sockaddr { unsigned short family; }
                if syscall.name == 'connect':
                    bytes = syscall.process.readBytes(syscall.arguments[1].value, syscall.arguments[2].value)
                    fdnum = syscall.arguments[0].value

                    resolved = resolve(syscall.process.pid, fdnum, 1)
                    if 'dst' in resolved:
                        proc.descriptors.get(fdnum).local = resolved['dst'] # TODO: rewrite
                elif syscall.name in ['accept', 'syscall<288>']:
                    bytes = syscall.process.readBytes(syscall.arguments[2].value, 4)
                    socket_size = unpack("I", bytes)[0]
                    bytes = syscall.process.readBytes(syscall.arguments[1].value, socket_size)
                    fdnum = syscall.result

                    self.get_descriptor(syscall.process.pid, syscall.arguments[0].value).server = True
                    self.get_descriptor(syscall.process.pid, syscall.arguments[0].value).used = 8

                    self.add_descriptor(syscall.process.pid, fd.Socket(self.data, fdnum, self.sockets))
                    self.get_descriptor(syscall.process.pid, fdnum).local = self.get_descriptor(syscall.process.pid, syscall.arguments[0].value).local
                    self.sockets += 1

                descriptor = proc.descriptors.get(fdnum)
                parsed = utils.parse_addr(bytes)
                descriptor.family = parsed.get_family()
                descriptor.remote = parsed
            elif syscall.name == 'dup2':
                a = syscall.arguments[0].value
                b = syscall.arguments[1].value

                proc.descriptors.close(b)
                proc.descriptors.clone(b, a)
            elif syscall.name == 'close':
                proc.descriptors.close(syscall.arguments[0].value)
            elif syscall.name == 'dup' or (syscall.name == 'fcntl' and syscall.arguments[1].value == 0): # F_DUPFD = 0
                new = syscall.result
                old = syscall.arguments[0].value
                proc.descriptors.clone(new, old)

        if syscall.name in ["read", "write", "sendmsg", "recvmsg", "sendto", "recvfrom"] and syscall.result > 0:
            family = {
                "read": "read",
                "write": "write",
                "sendmsg": "write",
                "recvmsg": "read",
                "sendto": "write",
                "recvfrom": "read"
            }[syscall.name]

            content = b""

            if syscall.name in ['sendmsg', 'recvmsg']:
                bytes = syscall.process.readBytes(syscall.arguments[1].value, 32)
                items = unpack("PIPL", bytes)

                for i in range(0, items[3]):
                    bytes = syscall.process.readBytes(items[2] + 16*i, 16)
                    i = unpack("PL", bytes)
                    content += syscall.process.readBytes(i[0], i[1])
            else:
                wrote = 0
                if family == 'read':
                    wrote = syscall.result
                else:
                    wrote = syscall.arguments[2].value
                content = syscall.process.readBytes(syscall.arguments[1].value, wrote)

            if family == 'read':
                proc.read(syscall.arguments[0].value, content)
            else:
                proc.write(syscall.arguments[0].value, content)

    def add_descriptor(self, pid, descriptor):
        self.pids[pid][descriptor.fd] = descriptor

    def get_descriptor(self, pid, descriptor):
        return self.pids[pid][descriptor]

    def close_descriptor(self, pid, descriptor):
        if descriptor not in self.pids[pid]:
            error("closing unknown socket")
            return

        if self.get_descriptor(pid, descriptor).used:
            self.data.get_process(pid)['descriptors'].append(self.get_descriptor(pid, descriptor))

        def removekey(d, key):
            r = dict(d)
            del r[key]
            return r

        self.pids[pid] = removekey(self.pids[pid], descriptor)

    def syscallTrace(self, process):
        # First query to break at next syscall
        self.prepareProcess(process)

        while True:
            # No more process? Exit
            if not self.debugger:
                break

            # Wait until next syscall enter
            try:
                event = self.debugger.waitSyscall()
                process = event.process
            except ProcessExit as event:
                self.processExited(event)
                continue
            except ProcessSignal as event:
                event.display()
                process.syscall(event.signum)
                continue
            except NewProcessEvent as event:
                self.newProcess(event)
                continue
            except ProcessExecution as event:
                self.processExecution(event)
                continue

            # Process syscall enter or exit
            self.syscall(process)

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(self.syscall_options)

        if syscall.name == "execve" and syscall.result is not None:
            proc = self.data.get_process(syscall.process.pid)
            proc['executable'] = syscall.arguments[0].text.strip("'")
            proc['arguments'] = utils.parseArgs(syscall.arguments[1].text)

            env = dict([i.split("=", 1) for i in utils.parseArgs(syscall.arguments[2].text)])
            proc['env'] = env

        if syscall and (syscall.result is not None):
            self.displaySyscall(syscall)

        # Break at next syscall
        process.syscall()

    def processExited(self, event):
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") \
        and (not self.options.enter) \
        and state.syscall:
            self.displaySyscall(state.syscall)

        # Display exit message
        error("*** %s ***" % event)
        self.data.get_process(event.process.pid)['exitCode'] = event.exitcode

        # TODO: close all
        #for fd, descriptor in self.pids[event.process.pid].items():
        #    self.close_descriptor(event.process.pid, fd)


    def prepareProcess(self, process):
        process.syscall()
        process.syscall_state.ignore_callback = self.ignoreSyscall

    def newProcess(self, event):
        process = event.process
        error("*** New process %s ***" % process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread)

        self.prepareProcess(process)
        process.parent.syscall()

    def processExecution(self, event):
        process = event.process
        error("*** Process %s execution ***" % process.pid)
        process.syscall()

    def runDebugger(self):
        # Create debugger and traced process
        self.setupDebugger()
        process = self.createProcess()
        if not process:
            return

        self.syscall_options = FunctionCallOptions()

        self.syscallTrace(process)

    def main(self):
        self.pids = {}
        self.debugger = PtraceDebugger()
        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()
        self.runDebugger()

        try:
            pass
            #self.runDebugger()
        except ProcessExit as event:
            self.processExited(event)
        except KeyboardInterrupt:
            error("Interrupted.")
            self.debugger.quit()
        except PTRACE_ERRORS as err:
            writeError(getLogger(), err, "Debugger error")
        except err:
            raise err
        self.debugger.quit()
        print(json.dumps(self.data.data, sort_keys=True, indent=4, cls=AppJSONEncoder))

        self.data.save()

    def createChild(self, program):
        pid = Application.createChild(self, program)
        error("execve(%s, %s, [/* 40 vars */]) = %s" % (program[0], program, pid))

        proc = self.data.new_process(pid, 0, False)
        proc['executable'] = program[0]
        proc['arguments'] = program
        proc['env'] = dict(os.environ)

        proc.descriptors.open(fd.File(self.data, 0, "stdin"))
        proc.descriptors.open(fd.File(self.data, 1, "stdout"))
        proc.descriptors.open(fd.File(self.data, 2, "stderr"))
        return pid

if __name__ == "__main__":
    SyscallTracer().main()
