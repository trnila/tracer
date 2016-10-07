import json
import os
import copy

from json_encode import AppJSONEncoder

class Capture:
    def __init__(self, descriptor):
        self.descriptor = descriptor

    def write(self, content):
        self.descriptor.write(content)

    def read(self, content):
        self.descriptor.read(content)

    def to_json(self):
        return self.descriptor.to_json()

class Descriptors:
    def __init__(self):
        self.descriptors = {}
        self.processes = []

    def open(self, descriptor):
        self.descriptors[descriptor.fd] = descriptor

    def close(self, descriptor):
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
        return self.descriptors[fd]


class Process:
    def __init__(self, data, descriptors):
        self.data = data
        self.descriptors = descriptors
        self.captures = {}

        self.descriptors.processes.append(self)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def read(self, fd, content):
        if fd not in self.captures or self.captures[fd] is None:
            self.captures[fd] = Capture(self.descriptors.get(fd))
            self.data['descriptors'].append(self.captures[fd])

        self.captures[fd].read(content)

    def write(self, fd, content):
        if fd not in self.captures or self.captures[fd] is None:
            self.captures[fd] = Capture(self.descriptors.get(fd))
            self.data['descriptors'].append(self.captures[fd])

        self.captures[fd].write(content)

    def on_close(self, fd):
        self.captures[fd] = None

    def to_json(self):
        return self.data


class Report:
    def __init__(self, path):
        self.data = {}
        self.path = path

        os.makedirs(path, exist_ok=True)

    def new_process(self, pid, parent, is_thread):
        self.data[pid] = Process({
            "pid": pid,
            "parent": parent,
            "exitCode": None,
            "executable": self.data[parent]['executable'] if parent else None,
            "arguments": self.data[parent]['arguments'] if parent else None,
            "thread": is_thread,
            "env": self.data[parent]['env'] if parent else None,
            "descriptors": []
        }, Descriptors())

        if parent:
            self.data[pid].descriptors = copy.deepcopy(self.data[parent].descriptors)

        #for id, descriptor in self.pids[process.pid].items():
        #    descriptor.change_id()

        return self.data[pid]

    def get_process(self, pid):
        return self.data[pid]

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self):
        with open(os.path.join(self.path, 'data.json'), 'w') as out:
            json.dump(self.data, out, sort_keys=True, indent=4, cls=AppJSONEncoder)
