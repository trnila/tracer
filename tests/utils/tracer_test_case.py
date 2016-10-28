import json
import os
import unittest
from subprocess import PIPE
from subprocess import Popen

from tests.utils.TracedData import System


class TracerTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_dir = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + "/../../")

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

        arguments = [self.project_dir + '/tracer.py'] + options + ['--', program] + args
        process = Popen(arguments, stdout=PIPE, stderr=PIPE, cwd=self.project_dir)
        stdout, stderr = process.communicate()
        # print(stdout.decode('utf-8'))
        # print(stderr.decode('utf-8'), file=sys.stderr)

        self.assertEqual(0, process.returncode)

        with open("/tmp/data.json") as file:
            return System("/tmp/", json.load(file))