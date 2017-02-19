ignore_files = [
    r'\/lib[^\/]+.so(\.[\d\-_]+)*$',  # .so shared libraries
    r'cache',
    r'^/usr/lib/locale/locale-archive$',
    r'^/usr/lib/gconv/gconv-modules$',
    r'^/usr/share/locale/locale.alias$'
]


# pass everything except pipes
def filter_out_descriptor(descriptor):
    return descriptor.is_pipe
