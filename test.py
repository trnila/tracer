import subprocess
from subprocess import Popen, PIPE
import json
import unittest
import shutil


def read(fileName):
    with open(fileName) as f:
        return f.read()

class TestStringMethods(unittest.TestCase):
    def test_me(self):
        path = shutil.which("uname")
        process = Popen(['python3', 'strace.py', path], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

        self.assertEqual(0, process.returncode)

        with open("/tmp/data.json") as file:
            data = json.load(file)
            root = list(data.keys())[0]

            p = data[root]

            self.assertEqual(path, p['executable'])
            self.assertEqual([path], p['arguments'])
            self.assertEqual(0, p['parent'])
            self.assertFalse(p['thread'])

            output = subprocess.Popen([path], stdout=subprocess.PIPE).communicate()[0]
            self.assertEqual(output.decode('utf-8'), read(p['write'][list(p['write'].keys())[0]]))


if __name__ == '__main__':
        unittest.main()
