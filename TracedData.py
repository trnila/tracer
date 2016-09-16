import json
import os


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

    def read_file(self, file_id):
        return open(os.path.join(self.path, file_id), 'rb').read()

    def append_file(self, file_id, content):
        with open(os.path.join(self.path, file_id), 'ab') as file:
            file.write(content)

    def save(self):
        with open(os.path.join(self.path, 'data.json'), 'w') as out:
            json.dump(self.data, out, sort_keys=True, indent=4)
