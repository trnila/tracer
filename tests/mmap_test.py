from .utils.tracer_test_case import TracerTestCase, project_dir


def get_region(process, region_id):
    for region in process['regions']:
        if region['region_id'] == region_id:
            return region
    return None


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

            regions = [
                get_region(process, maps[0]['region_id']),
                get_region(process, maps[1]['region_id']),
                get_region(process, maps[2]['region_id'])
            ]

            self.assertEqual(12, regions[0]['size'])
            self.assertEqual(12, regions[1]['size'])
            self.assertEqual(12, regions[2]['size'])

            self.assertEqual(['PROT_READ'], regions[0]['prot'])
            self.assertEqual(['MAP_PRIVATE'], regions[0]['flags'])

            self.assertEqual(['PROT_READ'], regions[1]['prot'])
            self.assertEqual(['MAP_SHARED'], regions[1]['flags'])

            self.assertEqual(['PROT_WRITE'], regions[2]['prot'])
            self.assertEqual(['MAP_SHARED'], regions[2]['flags'])

    def test_mmap_track(self):
        with self.execute('./examples/mmap/mmap_track2', options=['--trace-mmap']) as data:
            process = data.get_first_process()
            mmap = process.get_resource_by(type="file", path="%s/examples/100mb" % project_dir)['mmap'][0]

            regions = mmap['regions']
            region = get_region(process, mmap['region_id'])

            self.assertEqual(2, len(regions))
            self.assertEqual(region['address'], int(regions[0].split("-")[0], 16))
            self.assertEqual(region['address'] + region['size'], int(regions[1].split("-")[1], 16))

    def test_mmap_inherit(self):
        with self.execute('./examples/mmap/inherit') as data:
            self.assertEqual(2, len(data.processes))

            required = True
            for pid, process in data.processes.items():
                self.assertHave(process, 128)
                self.assertHave(process, 129, required)
                required = not required
