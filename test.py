import subprocess
from subprocess import Popen, PIPE
import json
import unittest

import sys

import os

import shutil
import utils
from pathlib import Path
from time import sleep


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
        print(stdout.decode('utf-8'))
        print(stderr.decode('utf-8'), file=sys.stderr)

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
        write = [p for i, p in root['write'].items() if p['type'] == 'socket'][0]
        read = [p for i, p in root['read'].items() if p['type'] == 'socket'][0]

        self.assertEqual('93.184.216.34', write['dst']['address'])
        self.assertEqual(80, write['dst']['port'])

        self.assertEqual('93.184.216.34', read['src']['address'])
        self.assertEqual(80, read['src']['port'])

        self.assertEqual(write['src']['port'], read['dst']['port'])
        self.assertEqual(write['src']['address'], read['dst']['address'])

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "ipv6 not supported on travis")
    def test_ipv6_resolve(self):
        data = self.execute('curl', ['http://[2606:2800:220:1:248:1893:25c8:1946]/'])
        root = data[list(data.keys())[0]]
        write = [p for i, p in root['write'].items() if p['type'] == 'socket'][0]
        read = [p for i, p in root['read'].items() if p['type'] == 'socket'][0]

        self.assertEqual('2606:2800:0220:0001:0248:1893:25c8:1946', write['dst']['address'])
        self.assertEqual(80, write['dst']['port'])

        self.assertEqual('2606:2800:0220:0001:0248:1893:25c8:1946', read['src']['address'])
        self.assertEqual(80, read['src']['port'])

        self.assertEqual(write['src']['port'], read['dst']['port'])
        self.assertEqual(write['src']['address'], read['dst']['address'])

    def test_unix(self):
        self.skipTest('not yet implemented')
        with open('/dev/null', 'w') as null:
            srv = Popen(['python3', 'strace.py', '-o', '/tmp/server', '--', 'python', 'examples/unix_socket_server.py'], stdout=null, stderr=null)
            sleep(2) # TODO: check when ready
            data = self.execute('sh', ['-c', 'echo hello world | nc -U /tmp/reverse.sock'])
            #print(json.dumps(data, sort_keys=True, indent=4))
            stdout, stderr = srv.communicate()
            with open("/tmp/data.json") as file:
                srv_data = json.load(file)

class TestUtils(unittest.TestCase):
    def test_empty(self):
        self.assertEqual([], utils.parseArgs("<>"))

    def test_simple(self):
        self.assertEqual(['ls'], utils.parseArgs("<'ls', NULL>"))

    def test_multiple(self):
        self.assertEqual(['ls', '-l', '/tmp'], utils.parseArgs("<'ls', '-l', '/tmp', NULL>"))

    def test_ipv4(self):
        self.assertEqual('93.184.216.34', utils.parse_ipv4('22D8B85D'))
        self.assertEqual('255.255.255.255', utils.parse_ipv4('ffffffff'))
        self.assertEqual('0.0.0.0', utils.parse_ipv4('00000000'))

    def test_ipv4_invalid(self):
        with self.assertRaises(ValueError):
            utils.parse_ipv4('inva')

    def test_ipv6(self):
        self.assertEqual('2606:2800:0220:0001:0248:1893:25c8:1946', utils.parse_ipv6('0028062601002002931848024619C825'))

if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
