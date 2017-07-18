from common import *

from sgfs.dirmap import DirMap


class TestDirMap(TestCase):

    def test_basics(self):

        map_ = DirMap([
            ('/src', '/dst'),
            ('/src/inner', '/dst2/inner'),
            ('/src3', '/dst3'),
        ])

        self.assertEqual(map_.get('/path/to/thing'), '/path/to/thing')

        self.assertEqual(map_.get('/src'), '/dst')
        self.assertEqual(map_.get('/src/inner'), '/dst2/inner')
        self.assertEqual(map_.get('/src3'), '/dst3')
        self.assertEqual(map_.get('/src/another'), '/dst/another')

    def test_empty(self):
        map_ = DirMap('')
        self.assertEqual(len(map_), 0)
        self.assertEqual(map_.get('/path/to/thing'), '/path/to/thing')

