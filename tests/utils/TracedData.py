import itertools
import json
import os

from tracer.json_encode import AppJSONEncoder


class Process:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def items(self):
        return self.data.items()

    def get_resource_by(self, **kwargs):
        def query(item, items):
            if item[0].endswith('__endswith'):
                return items[item[0].replace('__endswith', '')].endswith(item[1])

            return item in items.items()

        for descriptor in self.data['descriptors']:
            if kwargs and all(query(item, descriptor) for item in kwargs.items()):
                return descriptor
        return None


class System:
    def __init__(self, resource_path, data):
        self.processes = {}
        self.resource_path = resource_path

        for pid, process in data.items():
            self.processes[int(pid)] = Process(process)

    def all_resources(self):
        return list(itertools.chain(*[j['descriptors'] for i, j in self.processes.items()]))

    def get_first_process(self):
        return next(iter(self.processes.values()))

    def get_process_by(self, descriptors=None, **kwargs):
        if descriptors is None:
            descriptors = {}

        for pid, process in self.processes.items():
            if descriptors:
                for descriptor in process['descriptors']:
                    if all(item in descriptor.items() for item in descriptors.items()):
                        return process

            if kwargs and all(item in process.items() for item in kwargs.items()):
                return process
        return None

    def get_resource(self, pid):
        for i, proc in self.processes.items():
            for action in ['read', 'write']:
                for j, k in proc[action].items():
                    if pid == j:
                        return k
        return None

    def get_process_by_pid(self, pid):
        return self.processes[pid]

    def read_file(self, pid):
        with open(self.resource_path + "/" + pid, 'rb') as f:
            return f.read()


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
