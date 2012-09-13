from common import *


class TestCache(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
    
    def test_lookup_paths(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('Test Project ' + mini_uuid()))        
        sgfs.create_structure(proj)
        cache = sgfs.path_cache(proj)
        
        self.assertEqual(1, len(cache))
        self.assertEqual(cache.get(proj), os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_'))))
        
