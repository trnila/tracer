import json
import os

from json_encode import AppJSONEncoder


class Descriptors:
    pass

class Process:
    pass

class Report:
    def __init__(self, path):
        self.data = {}
        self.path = path

        os.makedirs(path, exist_ok=True)

    def new_process(self, pid, parent, is_thread):
        self.data[pid] = {
            "pid": pid,
            "parent": parent,
            "exitCode": None,
            "executable": self.data[parent]['executable'] if parent else None,
            "arguments": self.data[parent]['arguments'] if parent else None,
            "thread": is_thread,
            "env": self.data[parent]['env'] if parent else None,
            "descriptors": []
        }

        return self.data[pid]

    def get_process(self, pid):
        return self.data[pid]

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self):
        with open(os.path.join(self.path, 'data.json'), 'w') as out:
            json.dump(self.data, out, sort_keys=True, indent=4, cls=AppJSONEncoder)
