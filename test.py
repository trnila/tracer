import subprocess
from subprocess import Popen, PIPE
import json
import unittest
import sys
import os
import shutil
import utils
from time import sleep

from TracedData import System


def read(fileName):
    with open(fileName) as f:
        return f.read()


class TestQuery(unittest.TestCase):
    def test_simple_key(self):
        system = System("/tmp/", {
            12345: {
                "executable": "/bin/bash",
            },
            1111: {
                "executable": "/bin/cat"
            }
        })

        self.assertEqual(
            "/bin/cat",
            system.get_process_by(executable="/bin/cat")['executable']
        )

    def test_descriptor(self):
        system = System("/tmp/", {
            12345: {
                "executable": "/bin/bash",
                "descriptors": [
                    {
                        "type": "file",
                        "path": "/etc/passwd"
                    },
                    {
                        "type": "unix"
                    }
                ]
            },
            1111: {
                "executable": "/bin/cat",
                "descriptors": [
                    {
                        "type": "socket"
                    },
                    {
                        "type": "file",
                        "path": "/tmp/passwd"
                    }
                ]
            }
        })

        self.assertEqual(
            "/bin/cat",
            system.get_process_by(descriptors={"type": "file", "path": "/tmp/passwd"})['executable']
        )


class TestTracer(unittest.TestCase):
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
            return System("/tmp/", json.load(file))

    def test_simple(self):
        path = shutil.which("uname")
        data = self.execute(path)
        p = data.get_process_by(executable=shutil.which("uname"))

        self.assertEqual(path, p['executable'])
        self.assertEqual([path], p['arguments'])
        self.assertEqual(0, p['parent'])
        self.assertFalse(p['thread'])

        output = subprocess.Popen([path], stdout=subprocess.PIPE).communicate()[0]
        stdout = p.get_resource_by(type='file', path='stdout')
        self.assertEqual(output.decode('utf-8'), read('/tmp/' + stdout['write_content']))

    def test_pipes(self):
        data = self.execute("sh", ['-c', "cat /etc/passwd | tr a-z A-Z | tac"])

        sh = data.get_process_by(executable=shutil.which('sh'))
        cat = data.get_process_by(executable=shutil.which('cat'))
        tr = data.get_process_by(executable=shutil.which('tr'))
        tac = data.get_process_by(executable=shutil.which('tac'))

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
        pipe_src = cat.get_resource_by(type='pipe')
        pipe_dst = tr.get_resource_by(type='pipe', pipe_id=pipe_src['pipe_id'])
        self.assertFileEqual('/tmp/' + pipe_src['write_content'], '/tmp/' + pipe_dst['read_content'])

        pipe_src = tr.get_resource_by(type='pipe', pipe_id=1)
        pipe_dst = tac.get_resource_by(type='pipe', pipe_id=pipe_src['pipe_id'])
        self.assertFileEqual('/tmp/' + pipe_src['write_content'], '/tmp/' + pipe_dst['read_content'])

    def test_env_propagation(self):
        data = self.execute("sh", ['-c', 'export _MYENV=ok; sh -c "uname; ls"'])
        uname = data.get_process_by(executable=shutil.which('uname'))
        self.assertEqual('ok', uname['env']['_MYENV'])

    def test_exit_code(self):
        data = self.execute("cat", ['/nonexistent/file.txt'])
        uname = data.get_process_by(executable=shutil.which('cat'))
        self.assertEqual(1, uname['exitCode'])

    def test_ipv4_resolve(self):
        data = self.execute('curl', ['http://93.184.216.34/'])
        curl = data.get_process_by(executable=shutil.which('curl'))
        socket = curl.get_resource_by(type='socket')

        self.assertEqual('93.184.216.34', socket['remote']['address'])
        self.assertEqual(80, socket['remote']['port'])

        self.assertIsNotNone(socket['local']['address'])
        self.assertIsNotNone(socket['local']['port'])

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "ipv6 not supported on travis")
    def test_ipv6_resolve(self):
        data = self.execute('curl', ['http://[2606:2800:220:1:248:1893:25c8:1946]/'])
        curl = data.get_process_by(executable=shutil.which('curl'))
        socket = curl.get_resource_by(type='socket')

        self.assertEqual('2606:2800:220:1:248:1893:25c8:1946', socket['remote']['address'])
        self.assertEqual(80, socket['remote']['port'])
        self.assertIsNotNone(socket['local']['address'])
        self.assertIsNotNone(socket['local']['port'])

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

    def test_thread(self):
        data = self.execute('python', ['examples/threads.py'])

        process = data.get_process_by(thread=False)
        thread = data.get_process_by(thread=True)

        self.assertTrue(thread['thread'])
        self.assertFalse(process['thread'])
        self.assertEqual(process['executable'], thread['executable'])
        self.assertEqual(process['arguments'], thread['arguments'])
        self.assertEqual(process['env'], thread['env'])

    def test_thread_shared_fd(self):
        data = self.execute('python', ['examples/thread_fd_share.py'])

        process = data.get_process_by(thread=False)
        thread = data.get_process_by(thread=True)

        file = process.get_resource_by(type="file", path="/tmp/file")
        self.assertEqual("process", read('/tmp/' + file['write_content']))

        file = thread.get_resource_by(type="file", path="/tmp/file")
        self.assertEqual("thread", read('/tmp/' + file['write_content']))

    def test_process_change_fd_in_thread(self):
        data = self.execute('python', ['examples/thread_fail.py'])

        process = data.get_process_by(thread=False)
        thread = data.get_process_by(thread=True)

        file = process.get_resource_by(type="file", path="/tmp/file")
        self.assertEqual("test", read('/tmp/' + file['write_content']))

        file = thread.get_resource_by(type="file", path="/tmp/file")
        self.assertEqual("another", read('/tmp/' + file['write_content']))

    def test_multiple_reopen(self):
        data = self.execute('python', ['examples/multiple_read_write.py'])

        process = data.get_process_by(executable=shutil.which("python"))

        reads = ['first', 'firstsecond']
        writes = ['first', 'second']
        for capture in process['descriptors']:
            if capture['type'] == 'file' and capture['path'] == "/tmp/file":
                if 'read_content' in capture:
                    self.assertEqual(reads[0], read('/tmp/' + capture['read_content']))
                    reads.pop(0)
                else:
                    self.assertEqual(writes[0], read('/tmp/' + capture['write_content']))
                    writes.pop(0)

        self.assertEqual([], reads)
        self.assertEqual([], writes)




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
