import os
import sys
import unittest

from .utils.tracer_test_case import TracerTestCase


def extract_traces(traces):
    return [i['location'].split('/')[-1] for i in traces if i['location']]


@unittest.skipIf("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true", "not supported on travis")
class BacktraceTest(TracerTestCase):
    def assert_backtrace(self, expected, current):
        seq = [i for i in current if i in expected]
        self.assertEqual(expected, seq)

    def test_backtrace(self):
        with self.execute("./examples/backtrace/read_write_backtrace", options=['-b']) as data:
            p = data.get_first_process()
            file = p.get_resource_by(type='file', path='/tmp/file')

            # write
            expected = ['read_write_backtrace.c:11',
                        'read_write_backtrace.c:30',
                        'read_write_backtrace.c:34',
                        'read_write_backtrace.c:40']
            got = extract_traces(file['operations'][0]['backtrace'])
            self.assert_backtrace(expected, got)

            # write stdout
            stdout = p.get_resource_by(type="file", path="stdout")
            expected = ['read_write_backtrace.c:25', 'read_write_backtrace.c:35', 'read_write_backtrace.c:40']
            got = extract_traces(stdout['operations'][0]['backtrace'])
            self.assert_backtrace(expected, got)

            # read file
            file = [i for i in p['descriptors'] if i['type'] == 'file' and i['path'] == '/tmp/file' and 'read_content' in i][0]
            got = extract_traces(file['operations'][0]['backtrace'])
            expected = ['read_write_backtrace.c:21', 'read_write_backtrace.c:35', 'read_write_backtrace.c:40']
            self.assert_backtrace(expected, got)

    def test_multiple_sources(self):
        with self.execute("./examples/backtrace/more_sources/main", options=['-b']) as data:
            p = data.get_first_process()
            file = p.get_resource_by(type='file', path='stdout')

            expected = ['a.c:6', 'a.c:11', 'main.c:10']
            got = extract_traces(file['operations'][0]['backtrace'])
            self.assert_backtrace(expected, got)

            expected = ['main.c:7', 'a.c:7', 'a.c:11', 'main.c:10']
            got = extract_traces(file['operations'][1]['backtrace'])
            self.assert_backtrace(expected, got)

    def test_dynamic_lib(self):
        dir = "./examples/backtrace/dynamic_lib"

        with self.execute(dir + "/main", options=['-b'], env={'LD_LIBRARY_PATH': dir}) as data:
            p = data.get_first_process()
            file = p.get_resource_by(type='file', path='stdout')

            expected = ['dynamic.c:6', 'main.c:11']
            got = extract_traces(file['operations'][0]['backtrace'])
            self.assert_backtrace(expected, got)

            expected = ['main.c:8', 'dynamic.c:7', 'main.c:11']
            got = extract_traces(file['operations'][1]['backtrace'])
            self.assert_backtrace(expected, got)


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
