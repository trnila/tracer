def mmap_filter(region):
    if region.descriptor and region.descriptor['path'] == '/tmp/file' and region.process['executable'].endswith(
            'write_track'):
        return {
            "offset": 0,
            "size": 4
        }

    if region.size == 128:
        return True

    return False
