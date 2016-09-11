import subprocess
from subprocess import Popen, PIPE
import json
import unittest
import shutil


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

    def execute(self, program, args = []):
        process = Popen(['python3', 'strace.py', '-f', '--',  program] + args, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()

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
        self.assertEqual(output.decode('utf-8'), read(p['write'][list(p['write'].keys())[0]]))

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
        pipe = getKey(cat['write'], 'pipe:')
        self.assertFileEqual(cat['read'][getKey(cat['read'], '/etc/passwd')], '/etc/passwd')
        self.assertFileEqual(cat['write'][pipe], tr['read'][pipe])

        pipe = getKey(tr['write'], 'pipe:')
        self.assertFileEqual(tr['write'][pipe], tac['read'][pipe])

    def test_env_propagation(self):
        data = self.execute("sh", ['-c', 'export _MYENV=ok; sh -c "uname; ls"'])
        uname = findByExecutable(data, 'uname')
        self.assertEqual('ok', uname['env']['_MYENV'])



import utils
class TestUtils(unittest.TestCase):
    def test_empty(self):
        self.assertEqual([], utils.parseArgs("<>"))

    def test_simple(self):
        self.assertEqual(['ls'], utils.parseArgs("<'ls', NULL>"))

    def test_multiple(self):
        self.assertEqual(['ls', '-l', '/tmp'], utils.parseArgs("<'ls', '-l', '/tmp', NULL>"))

if __name__ == '__main__':
        unittest.main()
