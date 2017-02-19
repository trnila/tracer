import re


class Filter:
    def __init__(self, tracer):
        self.tracer = tracer
    
    def is_filtered(self, obj):
        return False
        filter_fn = getattr(self.tracer.options, 'pass_self', None)
        ignore_files = getattr(self.tracer.options, 'ignore_files', [])

        if 'descriptor' in self:
            for ignore in ignore_files:
                print('oj2!')
                if re.match(ignore, obj['path']):
                    return True

        if filter_fn:
            if not filter_fn(self):
                return True

        return False
