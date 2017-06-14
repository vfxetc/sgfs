from subprocess import call
import os

from common import *


class TestCache(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
    
    def test_lookup_paths(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('Test Project ' + mini_uuid()))        
        sgfs.create_structure(proj, allow_project=True)
        cache = sgfs.path_cache(proj)
        
        root = os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_')))
        
        self.assertEqual(1, len(cache))
        self.assertEqual(cache.get(proj), root)
        
        stat = os.stat(os.path.join(root, '.sgfs/cache.sqlite'))
        print oct(stat.st_mode)
        self.assertEqual(stat.st_mode & 0777, 0666)
    
    def test_assert_tag_exists(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('Test Project ' + mini_uuid()))        
        sgfs.create_structure(proj, allow_project=True)
        cache = sgfs.path_cache(proj)
        
        root = os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_')))
        os.unlink(os.path.join(root, '.sgfs.yml'))
        
        self.assertEqual(1, len(cache)) # This is still wierd, but expected.
        with capture_logs(silent=True) as logs:
            self.assertEqual(cache.get(proj), None)
        
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].levelname, 'WARNING')

        stat = os.stat(os.path.join(root, '.sgfs/cache.sqlite'))
        print oct(stat.st_mode)
        self.assertEqual(stat.st_mode & 0777, 0666)

    def test_old_cache_location(self):
        
        sgfs = SGFS(root=self.sandbox, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('Test Project ' + mini_uuid()))        
        sgfs.create_structure(proj, allow_project=True)

        root = os.path.abspath(os.path.join(self.sandbox, proj['name'].replace(' ', '_')))
        call(['mv', 
            os.path.join(root, '.sgfs/cache.sqlite'),
            os.path.join(root, '.sgfs-cache.sqlite'),
        ])

        cache = sgfs.path_cache(proj)
        
        self.assertEqual(1, len(cache))
        self.assertEqual(cache.get(proj), root)
    
    def test_out_of_root_paths(self):

        base = os.path.abspath(os.path.join(self.sandbox, 'multiroot'))
        root_a = os.path.join(base, 'root_a')
        root_b = os.path.join(base, 'root_b')

        os.makedirs(root_a)

        sgfs = SGFS(root=root_a, shotgun=self.sg)
        proj = sgfs.session.merge(self.fix.Project('NonLocalProject_' + mini_uuid()))
        sgfs.create_structure(proj, allow_project=True)
        cache = sgfs.path_cache(proj)

        proj_dir = cache.get(proj)

        pub_dir = os.path.join(root_b, os.path.relpath(proj_dir, root_a), 'PublishInRootB')
        os.makedirs(pub_dir)

        pub = self.fix.PublishEvent('PublishInRootB', project=proj)
        pub = sgfs.session.merge(pub)

        sgfs.tag_directory_with_entity(pub_dir, pub)

        # Assert that looking up via entity gets us the same path.
        path = sgfs.path_for_entity(pub)
        self.assertEqual(path, pub_dir)

        # Assert that looking up via path gets us the same entity.
        entities = sgfs.entities_from_path(pub_dir)
        self.assertEqual(len(entities), 1)
        self.assertIs(entities[0], pub)

        # Assert that the publish is within the root.
        # TODO: Implement this!
        self.assertRaises(ValueError, list, sgfs.entities_in_directory(root_b))

        pairs = list(sgfs.entities_in_directory(root_b, primary_root=proj_dir))
        self.assertEqual(len(pairs), 1)
        path, entity = pairs[0]
        self.assertIs(entity, pub)
        self.assertEqual(path, pub_dir)


        
