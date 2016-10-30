from .utils.tracer_test_case import TracerTestCase


class MmapTest(TracerTestCase):
    def test_mmap(self):
        data = self.execute('./examples/mmap')

        process = data.get_first_process()
        maps = process.get_resource_by(type="file", path="/tmp/file")['mmap']

        self.assertEqual(12, maps[0]['length'])
        self.assertEqual(12, maps[1]['length'])
        self.assertEqual(12, maps[2]['length'])

        import mmap
        self.assertEqual(mmap.PROT_READ, maps[0]['prot'])
        self.assertEqual(mmap.MAP_PRIVATE, maps[0]['flags'])

        self.assertEqual(mmap.PROT_READ, maps[1]['prot'])
        self.assertEqual(mmap.MAP_SHARED, maps[1]['flags'])

        self.assertEqual(mmap.PROT_WRITE, maps[2]['prot'])
        self.assertEqual(mmap.MAP_SHARED, maps[2]['flags'])

    def test_mmap_track(self):
        data = self.execute('./examples/mmap_track2', options=['--trace-mmap'])

        process = data.get_first_process()
        mmap = process.get_resource_by(type="file", path="%s/examples/100mb" % self.project_dir)['mmap'][0]
        regions = mmap['regions']

        self.assertEqual(2, len(regions))
        self.assertEqual(mmap['address'], int(regions[0].split("-")[0], 16))
        self.assertEqual(mmap['address'] + mmap['length'], int(regions[1].split("-")[1], 16))