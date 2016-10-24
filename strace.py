#!/usr/bin/env python
import json
import os
import random
import re
import socket
import string
import logging
from optparse import OptionParser
from struct import unpack
from sys import stderr, exit

from ptrace.debugger import (PtraceDebugger, Application,
    ProcessExit, ProcessSignal, NewProcessEvent, ProcessExecution)
from ptrace.error import PTRACE_ERRORS, writeError
from ptrace.func_call import FunctionCallOptions
from ptrace.syscall import (SYSCALL_NAMES, SYSCALL_PROTOTYPES,
                            FILENAME_ARGUMENTS)

import fd
import utils
from Report import Report, UnknownFd
from fd_resolve import resolve
from json_encode import AppJSONEncoder


logging.getLogger().setLevel(logging.DEBUG)
try:
    import colorlog
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)s:%(name)s:%(message)s'))
    colorlog.getLogger().addHandler(handler)
except:
    # color log is just optional feature
    pass


class SyscallTracer(Application):
    def __init__(self):
        Application.__init__(self)
        self.parseOptions()
        self.data = Report(self.options.output)
        self.pipes = 0
        self.sockets = 0

    def parseOptions(self):
        parser = OptionParser(usage="%prog [options] -- program [arg1 arg2 ...]")
        self.createCommonOptions(parser)
        parser.add_option('--output', '-o')

        self.createLogOptions(parser)

        self.options, self.program = parser.parse_args()

        if not self.options.output:
            self.options.output = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

        self.options.enter = True

        if self.options.pid is None and not self.program:
            parser.print_help()
            exit(1)

        self.processOptions()

    def displaySyscall(self, syscall):
        name = syscall.name
        text = syscall.format()
        if syscall.result is not None:
            text = "%-40s = %s" % (text, syscall.result_text)
        prefix = []
        prefix.append("[%s]" % syscall.process.pid)
        if prefix:
            text = ''.join(prefix) + ' ' + text
        logging.debug(text)

        proc = self.data.get_process(syscall.process.pid)

        if syscall.result >= 0 or syscall.result == -115: # EINPROGRESS
            if syscall.name == 'open':
                proc.descriptors.open(fd.File(self.data, syscall.result, syscall.arguments[0].text.strip('\'')))
            elif syscall.name == 'socket':
                descriptor = fd.Socket(self.data, syscall.result, self.sockets)
                descriptor.domain = syscall.arguments[0].value
                descriptor.type = syscall.arguments[1].value
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
                descriptor.server = True
                descriptor.used = 8
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

                    # mark accepting socket as server
                    descriptor = proc.descriptors.get(syscall.arguments[0].value)
                    descriptor.server = True
                    descriptor.used = 8

                    remote_desc = proc.descriptors.open(fd.Socket(self.data, fdnum, self.sockets))
                    remote_desc.local = proc.descriptors.get(syscall.arguments[0].value).local
                    self.sockets += 1

                descriptor = proc.descriptors.get(fdnum)
                parsed = utils.parse_addr(bytes)
                descriptor.domain = parsed.get_domain()
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
            elif syscall.name == 'mmap':
                if syscall.arguments[4].value != 18446744073709551615:
                    proc.mmap(syscall.arguments[4].value, {
                        'address': syscall.result,
                        'length': syscall.arguments[1].value,
                        'prot': syscall.arguments[2].value,
                        'flags': syscall.arguments[3].value
                    })

        if syscall.name == 'kill':
            proc['kills'].append({
                'pid': syscall.arguments[0].value,
                'signal': syscall.arguments[1].value
            })

        if syscall.name in ["read", "write", "sendmsg", "recvmsg", "sendto", "recvfrom"] and syscall.result > 0:
            descriptor = proc.descriptors.get(syscall.arguments[0].value)
            if isinstance(descriptor, fd.Socket) and descriptor.domain in [socket.AF_INET, socket.AF_INET6]:
                try:
                    if descriptor.local.address.__str__() == '0.0.0.0':
                        resolved = resolve(syscall.process.pid, syscall.arguments[0].value, 1)
                        descriptor.local = resolved['dst']
                except:
                    pass


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
                self.syscall(event.process)
            except ProcessExit as event:
                self.processExited(event)
            except ProcessSignal as event:
                event.display()
                event.process.syscall(event.signum)
            except NewProcessEvent as event:
                self.newProcess(event)
            except ProcessExecution as event:
                self.processExecution(event)


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
            try:
                self.displaySyscall(syscall)
            except UnknownFd as e:
                logging.fatal("Unknown FD!")

        # Break at next syscall
        process.syscall()

    def processExited(self, event):
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") and (not self.options.enter) and state.syscall:
            self.displaySyscall(state.syscall)

        # Display exit message
        logging.info("*** %s ***" % event)
        self.data.get_process(event.process.pid)['exitCode'] = event.exitcode

    def prepareProcess(self, process):
        process.syscall()

    def newProcess(self, event):
        process = event.process
        logging.info("*** New process %s ***" % process.pid)

        self.data.new_process(process.pid, process.parent.pid, process.is_thread)

        self.prepareProcess(process)
        process.parent.syscall()

    def processExecution(self, event):
        process = event.process
        logging.info("*** Process %s execution ***" % process.pid)
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
            logging.error("Interrupted.")
            self.debugger.quit()
        except PTRACE_ERRORS as err:
            writeError(logging.getLogger(), err, "Debugger error")
        except err:
            raise err
        self.debugger.quit()
        print(json.dumps(self.data.data, sort_keys=True, indent=4, cls=AppJSONEncoder))

        self.data.save()

    def createChild(self, program):
        pid = Application.createChild(self, program)
        logging.debug("execve(%s, %s, [/* 40 vars */]) = %s" % (program[0], program, pid))

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
