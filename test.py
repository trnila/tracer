import subprocess
from subprocess import Popen, PIPE
import json
import unittest


def read(fileName):
    with open(fileName) as f:
        return f.read()

class TestStringMethods(unittest.TestCase):
    def test_me(self):
        process = Popen(['python', 'strace.py', '/bin/uname'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

        self.assertEqual(0, process.returncode)

        with open("/tmp/data.json") as file:
            data = json.load(file)
            root = list(data.keys())[0]

            p = data[root]

            self.assertEqual("/bin/uname", p['executable'])
            self.assertEqual([], p['arguments'])
            self.assertEqual(0, p['parent'])
            self.assertFalse(p['thread'])

            output = subprocess.Popen(["/bin/uname"], stdout=subprocess.PIPE).communicate()[0]
            self.assertEqual(output.decode('utf-8'), read(p['write'][list(p['write'].keys())[0]]))


if __name__ == '__main__':
        unittest.main()
