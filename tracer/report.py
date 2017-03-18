import copy
import json
import os

import logging
from tracer import utils
from tracer.json_encode import AppJSONEncoder
from tracer.utils import AttributeTrait, build_repr


class UnknownFd(BaseException):
    pass


class Capture:
    def __init__(self, report, process, descriptor, nth):
        self.report = report
        self.process = process
        self.descriptor = descriptor
        self.nth = nth
        self.files = {}
        self.operations = []

    def write(self, content, **kwargs):
        self.__write('write', content, **kwargs)

    def read(self, content, **kwargs):
        self.__write('read', content, **kwargs)

    def read_from(self, content, **kwargs):
        self.__write('read', content, **kwargs)

    def to_json(self):
        return utils.merge_dicts(self.descriptor.to_json(), self.files, {'operations': self.operations})

    def __get_id(self):
        return "%s_%s_%s" % (self.process['pid'], self.descriptor.get_label(), self.nth)

    def __write(self, action, content, **kwargs):
        filename = self.__get_id() + "." + action

        self.files[action + '_content'] = filename
        self.report.append_file(filename, content)
        self.operations.append(utils.merge_dicts({'type': action, 'size': len(content)}, kwargs))

    def __setitem__(self, key, value):
        self.descriptor[key] = value

    def __getitem__(self, item):
        return self.descriptor[item]


class Descriptors:
    def __init__(self, filterer):
        self.descriptors = {}
        self.processes = []
        self.filter = filterer

    def open(self, descriptor):
        self.descriptors[descriptor.fd] = descriptor

        if self.filter.is_filtered(descriptor):
            descriptor.ignored = True

        for process in self.processes:
            process.open(descriptor)

        return descriptor

    def close(self, descriptor):
        if descriptor not in self.descriptors:
            raise UnknownFd(descriptor)

        def remove_key(descriptors, key):
            r = dict(descriptors)
            del r[key]
            return r

        self.descriptors = remove_key(self.descriptors, descriptor)

        for process in self.processes:
            process.on_close(descriptor)

    def clone(self, new, old):
        self.descriptors[new] = self.descriptors[old]

    def get(self, fd):
        if fd not in self.descriptors:
            raise UnknownFd(fd)
        return self.descriptors[fd]


class Process(AttributeTrait):
    def __init__(self, report, data, descriptors, tracer):
        super().__init__()
        self.report = report
        self.descriptors = descriptors
        self.captures = {}
        self.descriptors.processes.append(self)
        self.tracer = tracer
        self.attributes.update(data)
        self.rely = []

        for i, descriptor in self.descriptors.descriptors.items():
            self.open(descriptor)

        if self.parent:
            # sh
            fds = [int(i) for i in os.listdir("/proc/{}/fd".format(self.pid))]


            our = [pid for pid, v in self.descriptors.descriptors.items()]
            if our != fds:
                print(fds, our)
                os.system("ls -l /proc/{}/fd".format(self.pid))
                import sys
                logging.error('test')
                #sys.exit(1)

    @property
    def pid(self):
        return self['pid']

    @property
    def executable(self):
        return self['executable']

    @property
    def arguments(self):
        return self['arguments']

    @property
    def parent(self):
        if self['parent'] > 0:
            return self.report['processes'][self['parent']]
        return None

    def get_backtrace(self):
        return self.tracer.backend.create_backtrace(self.pid)

    def read_cstring(self, address):
        return self.tracer.backend.read_cstring(self.pid, address)

    def read_bytes(self, address, size):
        return self.tracer.backend.read_bytes(self.pid, address, size)

    def read(self, fd, content, **kwargs):
        self.captures[fd].read(content, **kwargs)

    def write(self, fd, content, **kwargs):
        self.captures[fd].write(content, **kwargs)

    def mmap(self, fd, params):
        self.captures[fd].descriptor['mmap'].append(params)

    def open(self, descriptor):
        self.__prepare_capture(descriptor['fd'])

    def on_close(self, fd):
        self.captures[fd] = None

    def to_json(self):
        #self.attributes['descriptors'] = [desc for desc in self.attributes['descriptors'] if
        #                                  not desc.descriptor.ignored]
        self.attributes['descriptors'] = self.rely
        return self.attributes

    def __prepare_capture(self, fd):
        if fd not in self.captures or self.captures[fd] is None:
            self.captures[fd] = Capture(self.report, self, self.descriptors.get(fd), len(self.rely))
            self.rely.append(self.captures[fd])

    def __str__(self):
        return "<Process {}>".format(
            build_repr(self, ['pid', 'executable', 'arguments'])
        )

    def __repr__(self):
        return self.__str__()


class Report(AttributeTrait):
    def __init__(self, path):
        super().__init__()
        self.data = {}
        self.path = path
        self.descriptor_groups = {}

        os.makedirs(path, exist_ok=True)

    def new_process(self, pid, parent, is_thread, tracer):
        if not is_thread:
            if parent:
                self.descriptor_groups[pid] = Descriptors(tracer.filter)
                self.descriptor_groups[pid].descriptors = copy.deepcopy(self.descriptor_groups[parent].descriptors)
                self.descriptor_groups[pid].processes = self.descriptor_groups[parent].processes
            else:
                self.descriptor_groups[pid] = Descriptors(tracer.filter)

            group = pid
        else:
            group = self._get_group(pid)

        self.processes[pid] = Process(self, {
            "pid": pid,
            "parent": parent,
            "exitCode": None,
            "executable": self.processes[parent]['executable'] if parent else None,
            "arguments": self.processes[parent]['arguments'] if parent else None,
            "thread": is_thread,
            "env": self.processes[parent]['env'] if parent else None,
            "descriptors": [],
            "kills": []
        }, self.descriptor_groups[group], tracer)

        if parent:
            self.processes[pid]['cwd'] = [self.processes[parent]['cwd'][-1]]


        return self.processes[pid]

    def get_process(self, pid):
        return self.processes[pid]

    @property
    def processes(self):
        return self['processes']

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self, out=None):
        if not out:
            with open(os.path.join(self.path, 'data.json'), 'w') as file:
                self.save(file)
        else:
            json.dump(self.attributes, out, sort_keys=True, indent=4, cls=AppJSONEncoder)

    def _get_group(self, pid):
        with open('/proc/%d/status' % pid) as f:
            return int(dict([(i, j.strip()) for i, j in [i.split(':', 1) for i in f.read().splitlines()]])['Tgid'])
