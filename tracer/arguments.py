from argparse import ArgumentParser


def create_core_parser():
    parser = ArgumentParser()
    parser.add_argument("--extension", "-e", help="path to extension file or directory to load",
                        action="append", default=[])
    parser.add_argument("-v", dest="logging_level", default=0, action="count")
    parser.add_argument('-p', dest="pid")
    parser.add_argument('--syscalls', '-s', help='print each syscall', action="store_true", default=False)
    parser.add_argument("program")
    parser.add_argument("arguments", nargs='*')

    return parser
