import subprocess


class Addr2line:
    def __init__(self, executable):
        self.executable = executable
        self.process = subprocess.Popen(["addr2line", "-e", executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def resolve(self, addr):
        self.process.stdin.write(("0x%x\n" % addr).encode('ascii'))
        self.process.stdin.flush()
        line = self.process.stdout.readline().decode('utf-8').strip()

        if line[0] == '/':
            return line
        return None