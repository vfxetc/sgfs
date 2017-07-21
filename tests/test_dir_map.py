from common import *


class TestDirMap(TestCase):


    def test_moved_project(self):

        src = os.path.join(self.sandbox, 'src')
        dst = os.path.join(self.sandbox, 'dst')

        os.makedirs(src)
        os.makedirs(dst)

        sgfs = SGFS(root=src)
        proj = self.fixture.Project('TestDirMap', sg_test_path=os.path.join(src, 'something'))
        sgfs.create_structure(proj, allow_project=True)

        os.rename(src, dst)

        sgfs = SGFS(root=dst, dir_map={src: dst})
        
        # The project has moved.
        proj_dir = sgfs.path_for_entity({'type': 'Project', 'id': proj['id']})
        self.assertEqual(proj_dir, os.path.join(dst, 'TestDirMap'))
        
        # A field within it has moved.
        proj = sgfs.entities_from_path(proj_dir)[0]
        self.assertEqual(proj['sg_test_path'], os.path.join(dst, 'something'))



