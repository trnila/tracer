import json
import os
import random
import re
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
import utils
from TracedData import TracedData


class SyscallTracer(Application):
    def __init__(self):
        Application.__init__(self)

        # Parse self.options
        self.parseOptions()
        self.data = TracedData(self.options.output)

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

        if syscall.process.pid not in self.data:
            self.addProcess(
                syscall.process.pid,
                syscall.process.parent.pid if syscall.process.parent else 0,
                syscall.process.is_thread
            )

        if syscall.name in ["read", "write", "sendmsg", "recvmsg", "sendto", "recvfrom"] and syscall.result > 0:
            type = {
                "read": "read",
                "write": "write",
                "sendmsg": "write",
                "recvmsg": "read",
                "sendto": "write",
                "recvfrom": "read"
            }[syscall.name]

            import fd_resolve
            data = fd_resolve.resolve(syscall.process.pid, syscall.arguments[0].value, type == 'read')


            if 'file' in data and '/usr/lib' in data['file']:
                return

            name = json.dumps(data, sort_keys=True)
            import hashlib
            name = hashlib.md5(name.encode('utf-8')).hexdigest()

            data['content'] = type + '_' + str(name)

            if name not in self.data[syscall.process.pid][type]:
                self.data[syscall.process.pid][type][name] = data
                # self.options.output + "/" + type + "__" + str(syscall.process.pid) + "_" + str(name)
            file = self.data[syscall.process.pid][type][name]['content']


            content = b""

            if syscall.name in ['sendmsg', 'recvmsg']:
                data = syscall.process.readBytes(syscall.arguments[1].value, 32)
                items = unpack("PIPL", data)

                for i in range(0, items[3]):
                    data = syscall.process.readBytes(items[2] + 16*i, 16)
                    i = unpack("PL", data)
                    content += syscall.process.readBytes(i[0], i[1])
            else:
                wrote = 0
                if type == 'read':
                    wrote = syscall.result
                else:
                    wrote = syscall.arguments[2].value
                content = syscall.process.readBytes(syscall.arguments[1].value, wrote)

            self.data.append_file(file, content)

    def addProcess(self, pid, parent, is_thread):
        self.data[pid] = {
            "pid": pid,
            "parent": parent,
            "exitCode": None,
            "executable": self.data[parent]['executable'] if parent else None,
            "arguments": self.data[parent]['arguments'] if parent else None,
            "thread": is_thread,
            "env": self.data[parent]['env'] if parent else None,
            "read": {},
            "write": {}
        }

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

        if syscall.process.pid not in self.data:
            self.addProcess(syscall.process.pid, syscall.process.parent.pid, syscall.process.is_thread)

        if syscall.name == "execve" and syscall.result is not None:
            self.data[syscall.process.pid]['executable'] = syscall.arguments[0].text.strip("'")
            self.data[syscall.process.pid]['arguments'] = utils.parseArgs(syscall.arguments[1].text)

            env = dict([i.split("=", 1) for i in utils.parseArgs(syscall.arguments[2].text)])
            self.data[syscall.process.pid]['env'] = env

        if syscall and (syscall.result is not None):
            self.displaySyscall(syscall)

        # Break at next syscall
        process.syscall()

    def parseCStringArray(self, address, syscall):
        text = []
        while True:
            str_addr = syscall.process.readWord(address)
            if not str_addr:
                break

            address += CPU_WORD_SIZE
            text.append(syscall.process.readCString(str_addr, 1000)[0].decode('utf-8'))
        return text

    def processExited(self, event):
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") \
        and (not self.options.enter) \
        and state.syscall:
            self.displaySyscall(state.syscall)

        # Display exit message
        error("*** %s ***" % event)
        self.data[event.process.pid]['exitCode'] = event.exitcode

    def prepareProcess(self, process):
        process.syscall()
        process.syscall_state.ignore_callback = self.ignoreSyscall

    def newProcess(self, event):
        process = event.process
        error("*** New process %s ***" % process.pid)
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
        self.debugger = PtraceDebugger()
        self.debugger.traceClone()
        self.debugger.traceExec()
        self.debugger.traceFork()
        try:
            self.runDebugger()
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
        print(json.dumps(self.data.data, sort_keys=True, indent=4))

        self.data.save()

    def createChild(self, program):
        pid = Application.createChild(self, program)
        error("execve(%s, %s, [/* 40 vars */]) = %s" % (program[0], program, pid))
        self.addProcess(pid, 0, False)
        self.data[pid]['executable'] = program[0]
        self.data[pid]['arguments'] = program
        self.data[pid]['env'] = dict(os.environ)
        return pid

if __name__ == "__main__":
    SyscallTracer().main()
