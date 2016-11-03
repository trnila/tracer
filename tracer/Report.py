import copy
import json
import os

from tracer.json_encode import AppJSONEncoder


class UnknownFd(BaseException):
    pass


class Capture:
    def __init__(self, report, process, descriptor, n):
        self.report = report
        self.process = process
        self.descriptor = descriptor
        self.n = n
        self.files = {}
        self.operations = []

    def write(self, content, backtrace):
        self.__write('write', content, backtrace)

    def read(self, content, backtrace):
        self.__write('read', content, backtrace)

    def to_json(self):
        return {**self.descriptor.to_json(), **self.files, **{'operations': self.operations}}

    def __get_id(self):
        return "%s_%s_%s" % (self.process['pid'], self.descriptor.get_label(), self.n)

    def __write(self, action, content, backtrace):
        filename = self.__get_id() + "." + action

        self.files[action + '_content'] = filename
        self.report.append_file(filename, content)
        self.operations.append({'type': action, 'size': len(content), 'backtrace': backtrace})


class Descriptors:
    def __init__(self):
        self.descriptors = {}
        self.processes = []

    def open(self, descriptor):
        self.descriptors[descriptor.fd] = descriptor
        return descriptor

    def close(self, descriptor):
        if descriptor not in self.descriptors:
            print("no descriptor")
            return

        def removekey(d, key):
            r = dict(d)
            del r[key]
            return r

        self.descriptors = removekey(self.descriptors, descriptor)

        for process in self.processes:
            process.on_close(descriptor)

    def clone(self, a, b):
        self.descriptors[a] = self.descriptors[b]

    def get(self, fd):
        if fd not in self.descriptors:
            raise UnknownFd
        return self.descriptors[fd]


class Process:
    def __init__(self, report, data, descriptors):
        self.report = report
        self.data = data
        self.descriptors = descriptors
        self.captures = {}
        self.descriptors.processes.append(self)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def read(self, fd, content, backtrace):
        self.__prepare_capture(fd)
        self.captures[fd].read(content, backtrace)

    def write(self, fd, content, backtrace):
        self.__prepare_capture(fd)
        self.captures[fd].write(content, backtrace)

    def mmap(self, fd, params):
        self.__prepare_capture(fd)
        self.captures[fd].descriptor.mmaps.append(params)

    def on_close(self, fd):
        self.captures[fd] = None

    def to_json(self):
        return self.data

    def __prepare_capture(self, fd):
        if fd not in self.captures or self.captures[fd] is None:
            self.captures[fd] = Capture(self.report, self, self.descriptors.get(fd), len(self.data['descriptors']))
            self.data['descriptors'].append(self.captures[fd])


class Report:
    def __init__(self, path):
        self.data = {}
        self.path = path
        self.descriptor_groups = {}

        os.makedirs(path, exist_ok=True)

    def new_process(self, pid, parent, is_thread):
        if not is_thread:
            if parent:
                self.descriptor_groups[pid] = copy.deepcopy(self.descriptor_groups[parent])
            else:
                self.descriptor_groups[pid] = Descriptors()

            group = pid
        else:
            group = self._get_group(pid)

        self.data[pid] = Process(self, {
            "pid": pid,
            "parent": parent,
            "exitCode": None,
            "executable": self.data[parent]['executable'] if parent else None,
            "arguments": self.data[parent]['arguments'] if parent else None,
            "thread": is_thread,
            "env": self.data[parent]['env'] if parent else None,
            "descriptors": [],
            "kills": []
        }, self.descriptor_groups[group])

        return self.data[pid]

    def get_process(self, pid):
        return self.data[pid]

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self, out=None):
        if not out:
            with open(os.path.join(self.path, 'data.json'), 'w') as out:
                self.save(out)
        else:
            json.dump(self.data, out, sort_keys=True, indent=4, cls=AppJSONEncoder)

    def _get_group(self, pid):
        with open('/proc/%d/status' % pid) as f:
            return int(dict([(i, j.strip()) for i, j in [i.split(':', 1) for i in f.read().splitlines()]])['Tgid'])
