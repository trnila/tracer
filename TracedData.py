import json
import os

from json_encode import AppJSONEncoder

import itertools


class Process:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def items(self):
        return self.data.items()

    def get_resource_by(self, **kwargs):
        for descriptor in self.data['descriptors']:
            if kwargs and all(item in descriptor.items() for item in kwargs.items()):
                return descriptor
        return None


class System:
    def __init__(self, resource_path, data):
        self.processes = {}
        self.resource_path = resource_path

        for id, process in data.items():
            self.processes[int(id)] = Process(process)

    def all_resources(self):
        return list(itertools.chain(*[j['descriptors'] for i, j in self.processes.items()]))

    def get_first_process(self):
        return next(iter(self.processes.values()))

    def get_process_by(self, descriptors={}, **kwargs):
        for pid, process in self.processes.items():
            if descriptors:
                for descriptor in process['descriptors']:
                    if all(item in descriptor.items() for item in descriptors.items()):
                        return process

            if kwargs and all(item in process.items() for item in kwargs.items()):
                return process
        return None

    def get_resource(self, id):
        for i, proc in self.processes.items():
            for type in ['read', 'write']:
                for j, k in proc[type].items():
                    if id == j:
                        return k
        return None

    def get_process_by_pid(self, pid):
        return self.processes[pid]

    def read_file(self, id):
        return open(self.resource_path + "/" + id, 'rb').read()

class TracedData:
    def __init__(self, path):
        self.data = {}
        self.path = path

        os.makedirs(path, exist_ok=True)

    def load(self):
        with open(os.path.join(self.path, 'data.json')) as file:
            self.data = json.load(file)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, item):
        return item in self.data

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self):
        with open(os.path.join(self.path, 'data.json'), 'w') as out:
            json.dump(self.data, out, sort_keys=True, indent=4, cls=AppJSONEncoder)
