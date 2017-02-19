import re


class Filter:
    def __init__(self, tracer):
        self.tracer = tracer
    
    def is_filtered(self, obj):
        filter_fn = getattr(self.tracer.options, 'pass_self', None)
        ignore_files = getattr(self.tracer.options, 'ignore_files', [])

        if obj.is_file:
            for ignore in ignore_files:
                if re.search(ignore, obj['path']):
                    return True

        if filter_fn:
            if not filter_fn(obj):
                return True

        return False
