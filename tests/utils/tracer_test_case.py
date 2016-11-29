import json
import os
import shutil
import tempfile
import unittest
from subprocess import PIPE
from subprocess import Popen

from tests.utils.TracedData import System

project_dir = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + "/../../")


class TracingResult:
    def __init__(self, output_dir, process):
        self.output_dir = output_dir
        self.process = process
        self.system = None

    def wait(self):
        stdout, stderr = self.process.communicate()
        #print(stdout.decode('utf-8'), stderr.decode('utf-8'))

        with open(self.output_dir + "/data.json") as file:
            self.system = System(self.output_dir, json.load(file))


class Tracing:
    def __init__(self, program, args=None, options=None, env=None, background=False):
        self.output_dir = tempfile.mkdtemp("tracer_report")
        self.program = program
        self.args = args if args else []
        self.options = (options if options else []) + ['-o', self.output_dir]
        self.env = env if env else {}
        self.background = background

    def __enter__(self):
        arguments = [project_dir + '/tracer.py'] + self.options + ['--', self.program] + self.args
        process = Popen(arguments, stdout=PIPE, stderr=PIPE, cwd=project_dir, env=self.env)

        res = TracingResult(self.output_dir, process)
        if not self.background:
            res.wait()
            return res.system
        else:
            return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.output_dir)


class TracerTestCase(unittest.TestCase):
    def assertFileEqual(self, file1, file2):
        with open(file1) as f1, open(file2) as f2:
            self.assertEqual(f1.read(), f2.read())

    def assertAllProcessExitedOk(self, data):
        for pid, proc in data.items():
            self.assertEqual(0, proc['exitCode'])

    def execute(self, program, arguments=[], **kwargs):
        resolved = shutil.which(program)
        return Tracing(resolved if resolved else program, arguments, **kwargs);
