import os
import shutil
import socket
import subprocess
import sys
import unittest
from time import sleep

from .utils.tracer_test_case import TracerTestCase

project_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))


class TracingTest(TracerTestCase):
    def test_simple(self):
        path = shutil.which("uname")
        with self.execute(path) as data:
            p = data.get_process_by(executable=shutil.which("uname"))

            self.assertEqual(path, p['executable'])
            self.assertEqual([path], p['arguments'])
            self.assertEqual(0, p['parent'])
            self.assertFalse(p['thread'])

            output = subprocess.Popen([path], stdout=subprocess.PIPE).communicate()[0]
            stdout = p.get_resource_by(type='file', path='stdout')
            self.assertEqual(output, data.read_file(stdout['write_content']))

    def test_pipes(self):
        with self.execute("sh", ['-c', "cat /etc/passwd | tr a-z A-Z | tac"]) as data:
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
            self.assertIsNotNone(pipe_src)
            self.assertIsNotNone(pipe_dst)
            self.assertEqual(data.read_file(pipe_src['write_content']), data.read_file(pipe_dst['read_content']))

            pipe_src = tr.get_resource_by(type='pipe', pipe_id=1)
            pipe_dst = tac.get_resource_by(type='pipe', pipe_id=pipe_src['pipe_id'])
            self.assertIsNotNone(pipe_src)
            self.assertIsNotNone(pipe_dst)
            self.assertEqual(data.read_file(pipe_src['write_content']), data.read_file(pipe_dst['read_content']))

    @unittest.skip
    def test_env_propagation(self):
        with self.execute("sh", ['-c', 'export _MYENV=ok; sh -c "uname; ls"']) as data:
            uname = data.get_process_by(executable=shutil.which('uname'))
            self.assertEqual('ok', uname['env']['_MYENV'])

    def test_exit_code(self):
        with self.execute("cat", ['/nonexistent/file.txt']) as data:
            uname = data.get_process_by(executable=shutil.which('cat'))
            self.assertEqual(1, uname['exitCode'])

    def test_ipv4_resolve(self):
        with self.execute('curl', ['http://93.184.216.34/']) as data:
            curl = data.get_process_by(executable=shutil.which('curl'))
            sock = curl.get_resource_by(type='socket')

            self.assertIsNotNone(sock)
            self.assertIsNotNone(sock['remote'])
            self.assertEqual('93.184.216.34', sock['remote']['address'])
            self.assertEqual(80, sock['remote']['port'])

            self.assertIsNotNone(sock['local']['address'])
            self.assertIsNotNone(sock['local']['port'])

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "ipv6 not supported on travis")
    def test_ipv6_resolve(self):
        with self.execute('curl', ['http://[2606:2800:220:1:248:1893:25c8:1946]/']) as data:
            curl = data.get_process_by(executable=shutil.which('curl'))
            sock = curl.get_resource_by(type='socket')

            self.assertEqual('2606:2800:220:1:248:1893:25c8:1946', sock['remote']['address'])
            self.assertEqual(80, sock['remote']['port'])
            self.assertIsNotNone(sock['local']['address'])
            self.assertIsNotNone(sock['local']['port'])

    def test_unix(self):
        with self.execute("./examples/sockets/unix_socket_server.py", background=True) as srv:
            sleep(1)  # TODO: check when ready
            with self.execute('sh', ['-c', 'echo hello world | nc -U /tmp/reverse.sock']) as client:
                proc = client.get_process_by(executable=shutil.which('nc'))
                sock = proc.get_resource_by(type='socket', domain=1)
                self.assertEqual("/tmp/reverse.sock", sock['remote'])

                srv.wait()
                srv = srv.system

                proc = srv.get_first_process()
                sock = proc.get_resource_by(type='socket', domain=1)
                self.assertEqual("/tmp/reverse.sock", sock['local'])

    def test_thread(self):
        with self.execute('python', ['examples/threads/threads.py']) as data:
            process = data.get_process_by(thread=False)
            thread = data.get_process_by(thread=True)

            self.assertTrue(thread['thread'])
            self.assertFalse(process['thread'])
            self.assertEqual(process['executable'], thread['executable'])
            self.assertEqual(process['arguments'], thread['arguments'])
            self.assertEqual(process['env'], thread['env'])

    def test_thread_shared_fd(self):
        with self.execute('examples/threads/thread_fd_share') as data:
            process = data.get_process_by(thread=False)
            thread = data.get_process_by(thread=True)

            file = process.get_resource_by(type="file", path="/tmp/file")
            self.assertEqual("process", data.read_file(file['write_content']).decode('utf-8'))
            self.assertEqual(process['pid'], file['opened_pid'])

            file = thread.get_resource_by(type="file", path="/tmp/file")
            self.assertEqual("thread", data.read_file(file['write_content']).decode('utf-8'))
            self.assertEqual(process['pid'], file['opened_pid'])

    def test_process_change_fd_in_thread(self):
        with self.execute('python', ['examples/threads/thread_fail.py']) as data:
            process = data.get_process_by(thread=False)
            thread = data.get_process_by(thread=True)

            file = process.get_resource_by(type="file", path="/tmp/file")
            self.assertEqual("test", data.read_file(file['write_content']).decode('utf-8'))

            file = thread.get_resource_by(type="file", path="/tmp/file")
            self.assertEqual("another", data.read_file(file['write_content']).decode('utf-8'))

    def test_multiple_reopen(self):
        with self.execute('python', ['examples/files/multiple_read_write.py']) as data:
            process = data.get_process_by(executable=shutil.which("python"))

            reads = ['first', 'firstsecond']
            writes = ['first', 'second']
            for capture in process['descriptors']:
                if capture['type'] == 'file' and capture['path'] == "/tmp/file":
                    if 'read_content' in capture:
                        self.assertEqual(reads[0], data.read_file(capture['read_content']).decode('utf-8'))
                        reads.pop(0)
                    else:
                        self.assertEqual(writes[0], data.read_file(capture['write_content']).decode('utf-8'))
                        writes.pop(0)

            self.assertEqual([], reads)
            self.assertEqual([], writes)

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "not supported on travis")
    def test_udp4_send(self):
        with self.execute('bash', ['-c', 'echo hello > /dev/udp/127.0.0.1/1234']) as data:
            process = data.get_first_process()
            sock = process.get_resource_by(type="socket")

            self.assertEqual("127.0.0.1", sock['local']['address'])
            self.assertEqual("127.0.0.1", sock['remote']['address'])
            self.assertEqual(1234, sock['remote']['port'])
            self.assertEqual(socket.AF_INET, sock['domain'])
            self.assertEqual(socket.SOCK_DGRAM, sock['socket_type'])

    @unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "not supported on travis")
    def test_udp6_send(self):
        with self.execute('bash', ['-c', 'echo hello > /dev/udp/::1/1234']) as data:
            process = data.get_first_process()
            sock = process.get_resource_by(type="socket")

            self.assertEqual("::1", sock['local']['address'])
            self.assertEqual("::1", sock['remote']['address'])
            self.assertEqual(1234, sock['remote']['port'])
            self.assertEqual(socket.AF_INET6, sock['domain'])
            self.assertEqual(socket.SOCK_DGRAM, sock['socket_type'])

    def test_signals(self):
        with self.execute('./examples/signals/signals') as data:
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
        with self.execute('./examples/signals/signals_kill_child') as data:
            parent = list(data.processes.values())[0]
            child = list(data.processes.values())[1]

            import signal
            self.assertGreaterEqual(1, len(parent['kills']))
            self.assertEqual(child['pid'], parent['kills'][0]['pid'])
            self.assertEqual(signal.SIGKILL, parent['kills'][0]['signal'])
            # TODO: add that this process has been killed?

    def test_open(self):
        with self.execute('./examples/files/openat') as data:
            proc = data.get_first_process()
            self.assertIsNotNone(proc.get_resource_by(path="{}/requirements.txt".format(project_dir)))
            self.assertIsNotNone(proc.get_resource_by(path="{}/examples/files/openat.c".format(project_dir)))
            self.assertIsNotNone(proc.get_resource_by(path="/etc/passwd"))
            self.assertIsNotNone(proc.get_resource_by(path="/proc/meminfo"))
            self.assertIsNotNone(proc.get_resource_by(path="{}/examples/Makefile".format(project_dir)))

    def test_quit(self):
        with self.execute('cat', background=True) as data:
            sleep(1)
            data.process.terminate()
            data.wait()
            self.assertEqual(0, data.process.returncode);
            self.assertIsNotNone(data.system.get_process_by(executable=shutil.which("cat")))


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
