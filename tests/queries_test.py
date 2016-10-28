import sys
import unittest

from tests.utils.TracedData import System


class QueriesTest(unittest.TestCase):
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

if __name__ == '__main__':
    sys.argv.append('-b')
    unittest.main()
