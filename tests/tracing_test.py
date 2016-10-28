import json
import os
import shutil
import socket
import subprocess
import sys
import unittest
from subprocess import Popen, PIPE
from time import sleep

from tracer.TracedData import System

project_dir = os.path.dirname(os.path.realpath(__file__)) + "/../"


def read(file_name):
    with open(file_name) as f:
        return f.read()


class TracingTest(unittest.TestCase):
    def assertFileEqual(self, file1, file2):
        with open(file1) as f1, open(file2) as f2:
            self.assertEqual(f1.read(), f2.read())

    def assertAllProcessExitedOk(self, data):
        for pid, proc in data.items():
            self.assertEqual(0, proc['exitCode'])

    def execute(self, program, args=None, options=None):
        if args is None:
            args = []

        if options is None:
            options = []

        options = ['-o', '/tmp/'] + options

        process = Popen(['python3', 'tracer.py'] + options + ['--',  program] + args, stdout=PIPE, stderr=PIPE, cwd=project_dir)
        stdout, stderr = process.communicate()
        #print(stdout.decode('utf-8'))
        #print(stderr.decode('utf-8'), file=sys.stderr)

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
        sock = curl.get_resource_by(type='socket')

        self.assertEqual('93.184.216.34', sock['remote']['address'])
        self.assertEqual(80, sock['remote']['port'])

        self.assertIsNotNone(sock['local']['address'])
        self.assertIsNotNone(sock['local']['port'])

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "ipv6 not supported on travis")
    def test_ipv6_resolve(self):
        data = self.execute('curl', ['http://[2606:2800:220:1:248:1893:25c8:1946]/'])
        curl = data.get_process_by(executable=shutil.which('curl'))
        sock = curl.get_resource_by(type='socket')

        self.assertEqual('2606:2800:220:1:248:1893:25c8:1946', sock['remote']['address'])
        self.assertEqual(80, sock['remote']['port'])
        self.assertIsNotNone(sock['local']['address'])
        self.assertIsNotNone(sock['local']['port'])

    def test_unix(self):
        with open('/dev/null', 'w') as null:
            srv = Popen(['python3', 'tracer.py', '-o', '/tmp/server', '--', 'python', 'examples/unix_socket_server.py'],
                        stdout=null, stderr=null, cwd=project_dir)
            sleep(4)  # TODO: check when ready
            data = self.execute('sh', ['-c', 'echo hello world | nc -U /tmp/reverse.sock'])
            stdout, stderr = srv.communicate()
            with open("/tmp/data.json") as file:
                srv_data = System("/tmp/", json.load(file))
                proc = srv_data.get_process_by(executable=shutil.which('nc'))

                sock = proc.get_resource_by(type='socket', domain=1)
                self.assertEqual("/tmp/reverse.sock", sock['remote'])
                self.assertEqual(False, sock['server'])

            proc = srv_data.get_process_by(executable=shutil.which('nc'))
            sock = proc.get_resource_by(type='socket', domain=1)
            self.assertEqual("/tmp/reverse.sock", sock['remote'])

            self.skipTest("is server supported?")
            self.assertEqual(True, sock['server'])

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
        data = self.execute('examples/thread_fd_share')

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

    def test_udp4_send(self):
        data = self.execute('sh', ['-c', 'echo hello > /dev/udp/127.0.0.1/1234'])

        process = data.get_process_by(executable=shutil.which("sh"))
        sock = process.get_resource_by(type="socket")

        self.assertEqual("127.0.0.1", sock['local']['address'])
        self.assertEqual("127.0.0.1", sock['remote']['address'])
        self.assertEqual(1234, sock['remote']['port'])
        self.assertEqual(socket.AF_INET, sock['domain'])
        self.assertEqual(socket.SOCK_DGRAM, sock['socket_type'])

    def test_udp6_send(self):
        data = self.execute('sh', ['-c', 'echo hello > /dev/udp/::1/1234'])

        process = data.get_process_by(executable=shutil.which("sh"))
        sock = process.get_resource_by(type="socket")

        self.assertEqual("::1", sock['local']['address'])
        self.assertEqual("::1", sock['remote']['address'])
        self.assertEqual(1234, sock['remote']['port'])
        self.assertEqual(socket.AF_INET6, sock['domain'])
        self.assertEqual(socket.SOCK_DGRAM, sock['socket_type'])

    def test_mmap(self):
        data = self.execute('./examples/mmap')

        process = data.get_first_process()
        maps = process.get_resource_by(type="file", path="/tmp/file")['mmap']

        self.assertEqual(12, maps[0]['length'])
        self.assertEqual(12, maps[1]['length'])
        self.assertEqual(12, maps[2]['length'])

        import mmap
        self.assertEqual(mmap.PROT_READ, maps[0]['prot'])
        self.assertEqual(mmap.MAP_PRIVATE, maps[0]['flags'])

        self.assertEqual(mmap.PROT_READ, maps[1]['prot'])
        self.assertEqual(mmap.MAP_SHARED, maps[1]['flags'])

        self.assertEqual(mmap.PROT_WRITE, maps[2]['prot'])
        self.assertEqual(mmap.MAP_SHARED, maps[2]['flags'])

    def test_signals(self):
        data = self.execute('./examples/signals')

        parent = data.get_process_by(parent=0)
        child = data.get_process_by(parent=parent['pid'])

        import signal
        self.assertGreaterEqual(1, len(child['kills']))
        self.assertEqual(parent['pid'], child['kills'][0]['pid'])
        self.assertEqual(signal.SIGUSR1, child['kills'][0]['signal'])

        self.assertGreaterEqual(1, len(parent['kills']))
        self.assertEqual(child['pid'], parent['kills'][0]['pid'])
        self.assertEqual(signal.SIGUSR2, parent['kills'][0]['signal'])

    def test_signal_kill_child(self):
        data = self.execute('./examples/signals_kill_child')

        parent = list(data.processes.values())[0]
        child = list(data.processes.values())[1]

        import signal
        self.assertGreaterEqual(1, len(parent['kills']))
        self.assertEqual(child['pid'], parent['kills'][0]['pid'])
        self.assertEqual(signal.SIGKILL, parent['kills'][0]['signal'])
        # TODO: add that this process has been killed?

    def test_mmap_track(self):
        data = self.execute('./examples/mmap_track2', options=['--trace-mmap'])

        process = data.get_first_process()
        mmap = process.get_resource_by(type="file", path=os.path.realpath("%s/../examples/100mb" % (os.getcwd())))['mmap'][0]
        regions = mmap['regions']

        self.assertEqual(2, len(regions))
        self.assertEqual(mmap['address'], int(regions[0].split("-")[0], 16))
        #self.assertLessEqual(mmap['address'] + mmap['length'], int(regions[1].split("-")[1], 16))

if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
