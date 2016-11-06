import sys
import unittest

from .utils.tracer_test_case import TracerTestCase


def extract_traces(traces):
    return [i['location'].split('/')[-1] for i in traces if i['location']]


class BacktraceTest(TracerTestCase):
    def test_backtrace(self):
        data = self.execute("./examples/backtrace/read_write_backtrace", options=['-b'])
        p = data.get_first_process()
        file = p.get_resource_by(type='file', path='/tmp/file')

        # write
        expected = ['read_write_backtrace.c:11',
                    'read_write_backtrace.c:30',
                    'read_write_backtrace.c:34',
                    'read_write_backtrace.c:40']
        got = extract_traces(file['operations'][0]['backtrace'])
        self.assertEqual(expected, got)

        # write stdout
        stdout = p.get_resource_by(type="file", path="stdout")
        expected = ['read_write_backtrace.c:25', 'read_write_backtrace.c:35', 'read_write_backtrace.c:40']
        got = extract_traces(stdout['operations'][0]['backtrace'])
        self.assertEqual(expected, got)

        # read file
        file = [i for i in p['descriptors'] if i['type'] == 'file' and i['path'] == '/tmp/file' and 'read_content' in i][0]
        got = extract_traces(file['operations'][0]['backtrace'])
        expected = ['read_write_backtrace.c:21', 'read_write_backtrace.c:35', 'read_write_backtrace.c:40']
        self.assertEqual(got, expected)

    def test_multiple_sources(self):
        data = self.execute("./examples/backtrace/more_sources/main", options=['-b'])
        p = data.get_first_process()
        file = p.get_resource_by(type='file', path='stdout')

        expected = ['a.c:6', 'a.c:11', 'main.c:10']
        got = extract_traces(file['operations'][0]['backtrace'])
        self.assertEqual(expected, got)

        expected = ['main.c:7', 'a.c:7', 'a.c:11', 'main.c:10']
        got = extract_traces(file['operations'][1]['backtrace'])
        self.assertEqual(expected, got)

    def test_dynamic_lib(self):
        dir = "./examples/backtrace/dynamic_lib"

        data = self.execute(dir + "/main", options=['-b'], env={'LD_LIBRARY_PATH': dir})
        p = data.get_first_process()
        file = p.get_resource_by(type='file', path='stdout')

        expected = ['dynamic.c:6', 'main.c:11']
        got = extract_traces(file['operations'][0]['backtrace'])
        self.assertEqual(expected, got)

        expected = ['main.c:8', 'dynamic.c:7', 'main.c:11']
        got = extract_traces(file['operations'][1]['backtrace'])
        self.assertEqual(expected, got)


if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()