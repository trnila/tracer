import subprocess
from subprocess import Popen, PIPE
import json
import unittest
import shutil
import os
from pathlib import Path


def read(fileName):
    with open(fileName) as f:
        return f.read()

def findByExecutable(data, exe):
    for pid, process in data.items():
        if exe in process['executable']:
            return process

def getKey(data, startsWith):
    return [i for i in data.keys() if i.startswith(startsWith)][0]


class TestStringMethods(unittest.TestCase):
    def assertFileEqual(self, file1, file2):
        with open(file1) as f1, open(file2) as f2:
            self.assertEqual(f1.read(), f2.read())

    def assertAllProcessExitedOk(self, data):
        for pid, proc in data.items():
            self.assertEqual(0, proc['exitCode'])

    def execute(self, program, args = []):
        process = Popen(['python3', 'strace.py', '-o', '/tmp', '-f', '--',  program] + args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

        path = '/tmp/output/' + self._testMethodName
        Path(path).mkdir(parents=True, exist_ok=True)
        with open(path + "/stdout", 'w') as out:
            out.write(stdout.decode('utf-8'))
        with open(path + "/stderr", 'w') as out:
            out.write(stderr.decode('utf-8'))

        self.assertEqual(0, process.returncode)

        with open("/tmp/data.json") as file:
            return json.load(file)


    def test_simple(self):
        path = shutil.which("uname")
        data = self.execute(path)
        root = list(data.keys())[0]

        p = data[root]

        self.assertEqual(path, p['executable'])
        self.assertEqual([path], p['arguments'])
        self.assertEqual(0, p['parent'])
        self.assertFalse(p['thread'])

        output = subprocess.Popen([path], stdout=subprocess.PIPE).communicate()[0]
        self.assertEqual(output.decode('utf-8'), read('/tmp/' + p['write'][list(p['write'].keys())[0]]['content']))

    def test_pipes(self):
        data = self.execute("sh", ['-c', "cat /etc/passwd | tr a-z A-Z | tac"])
        #print(json.dumps(data, sort_keys=True, indent=4))

        sh = findByExecutable(data, 'sh')
        cat = findByExecutable(data, 'cat')
        tr = findByExecutable(data, 'tr')
        tac = findByExecutable(data, 'tac')

        # check arguments
        self.assertEqual([shutil.which("sh"), '-c', 'cat /etc/passwd | tr a-z A-Z | tac'], sh['arguments'])
        self.assertEqual(["cat", '/etc/passwd'], cat['arguments'])
        self.assertEqual(["tr", 'a-z', 'A-Z'], tr['arguments'])
        self.assertEqual(["tac"], tac['arguments'])

        # check parents
        self.assertEqual(0, sh['parent'])
        self.assertEqual(sh['pid'], cat['parent'])
        self.assertEqual(sh['pid'], tr['parent'])
        self.assertEqual(sh['pid'], tac['parent'])

        # check pipe
        pipe = [i for i, c in cat['write'].items() if c['type'] == 'pipe'][0]
        self.assertFileEqual('/tmp/' + cat['write'][pipe]['content'], '/tmp/' + tr['read'][pipe]['content'])

        pipe = [i for i, c in tr['write'].items() if c['type'] == 'pipe'][0]
        self.assertFileEqual('/tmp/' + tr['write'][pipe]['content'], '/tmp/' + tac['read'][pipe]['content'])

    def test_env_propagation(self):
        data = self.execute("sh", ['-c', 'export _MYENV=ok; sh -c "uname; ls"'])
        uname = findByExecutable(data, 'uname')
        self.assertEqual('ok', uname['env']['_MYENV'])

    def test_exit_code(self):
        data = self.execute("cat", ['/nonexistent/file.txt'])
        uname = findByExecutable(data, 'cat')
        self.assertEqual(1, uname['exitCode'])

    def test_ipv4_resolve(self):
        data = self.execute('curl', ['http://93.184.216.34/'])
        root = data[list(data.keys())[0]]
        file = [p for i, p in root['write'].items() if p['type'] == 'socket'][0]

        self.assertEqual('93.184.216.34', file['dst']['address'])
        self.assertEqual(80, file['dst']['port'])



import utils
class TestUtils(unittest.TestCase):
    def test_empty(self):
        self.assertEqual([], utils.parseArgs("<>"))

    def test_simple(self):
        self.assertEqual(['ls'], utils.parseArgs("<'ls', NULL>"))

    def test_multiple(self):
        self.assertEqual(['ls', '-l', '/tmp'], utils.parseArgs("<'ls', '-l', '/tmp', NULL>"))

class Ipv4Test(unittest.TestCase):
    def test_ipv4(self):
        self.assertEqual('93.184.216.34', utils.parse_ipv4('22D8B85D'))
        self.assertEqual('255.255.255.255', utils.parse_ipv4('ffffffff'))
        self.assertEqual('0.0.0.0', utils.parse_ipv4('00000000'))

    def test_ipv4_invalid(self):
        with self.assertRaises(ValueError):
            utils.parse_ipv4('inva')

if __name__ == '__main__':
        unittest.main()
