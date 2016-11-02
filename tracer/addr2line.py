import subprocess

class Addr2line:
    def __init__(self, executable):
        self.executable = executable
        self.process = subprocess.Popen(["addr2line", "-e", executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.cache = {}

    def resolve(self, addr):
        if addr in self.cache:
            return self.cache[addr]

        self.process.stdin.write(("0x%x\n" % addr).encode('ascii'))
        self.process.stdin.flush()
        line = self.process.stdout.readline().decode('utf-8').strip()
        self.cache[addr] = line if line[0] == '/' else None

        return self.cache[addr]