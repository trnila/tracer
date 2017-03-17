from .utils.tracer_test_case import TracerTestCase, project_dir


class MmapTest(TracerTestCase):
    def assertHave(self, process, size, required=True):
        found = False
        for region in process.data.get('regions', []):
            if region['size'] == size:
                found = True

        if required and not found:
            self.fail("Region with size {} missing".format(size))
        elif not required and found:
            self.fail("Region with size {} found".format(size))

    def test_mmap(self):
        with self.execute('./examples/mmap/mmap') as data:
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
        with self.execute('./examples/mmap/mmap_track2', options=['--trace-mmap']) as data:
            process = data.get_first_process()
            mmap = process.get_resource_by(type="file", path="%s/examples/100mb" % project_dir)['mmap'][0]

            regions = mmap['regions']

            self.assertEqual(2, len(regions))
            self.assertEqual(mmap['address'], int(regions[0].split("-")[0], 16))
            self.assertEqual(mmap['address'] + mmap['length'], int(regions[1].split("-")[1], 16))

    def test_mmap_inherit(self):
        with self.execute('./examples/mmap/inherit') as data:
            self.assertEqual(2, len(data.processes))

            required = True
            for pid, process in data.processes.items():
                self.assertHave(process, 128)
                self.assertHave(process, 129, required)
                required = not required