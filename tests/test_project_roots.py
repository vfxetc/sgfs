from common import *


class TestSingleproject(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
    
    def test_single_project(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('Test Project ' + mini_uuid()))
        sgfs.create_structure(proj, allow_project=True)
        
        self.assertEqual(1, len(sgfs.project_roots))
        self.assertEqual(sgfs.project_roots[proj], os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_'))))
        
        # New SGFS, but old Entity; there be dragons in this block!
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        self.assertEqual(1, len(sgfs.project_roots))
        self.assertSameEntity(sgfs.project_roots.keys()[0], proj)
        self.assertIsNot(sgfs.project_roots.keys()[0], proj)
        self.assertEqual(sgfs.project_roots.values()[0], os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_'))))
        
        proj = sgfs.session.find_one('Project', [('id', 'is', proj['id'])])
        self.assertEqual(1, len(sgfs.project_roots))
        self.assertSameEntity(sgfs.project_roots.keys()[0], proj)
        self.assertIs(sgfs.project_roots.keys()[0], proj)
        

class TestMultipleProjects(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
    
    def test_multiple_projects(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        for i in range(1, 5):
            proj = sgfs.session.merge(self.fix.Project(('Test Project %d ' % i) + mini_uuid()))
            sgfs.create_structure(proj, allow_project=True)
        
        self.assertEqual(4, len(sgfs.project_roots))
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        self.assertEqual(4, len(sgfs.project_roots))
        
