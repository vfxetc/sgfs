from subprocess import call
import re

from common import *


class _AnyNumber(int):
    def __eq__(self, other):
        return True
ANY = _AnyNumber(1)


class PathTester(object):
    
    def __init__(self, test, root):
        self.test = test
        self.root = root
        
        self.paths = []
        self.matched = set()
        self.scan()
    
    def scan(self):
        
        paths = []
        
        for dir_name, dir_names, file_names in os.walk(self.root):
            for name in dir_names:
                path = os.path.join(dir_name, name)[len(self.root):] + '/'
                paths.append(path)
            for name in file_names:
                path = os.path.join(dir_name, name)[len(self.root):]
                paths.append(path)
        
        for pattern in (r'\._', r'\.DS_Store$', r'.*\.pyc$'):
            paths = [path for path in paths if not re.match(pattern, path)]
        
        paths = [x for x in paths if x not in self.matched]
        self.paths.extend(paths)
        
        print 'PathTester found', len(paths), 'new items'
        # if paths:
        #    print '\n'.join('\t' + x for x in sorted(paths))
    
    def __enter__(self):
        self.scan()
    
    def __exit__(self, *args):
        self.assertMatchedAll()
        
    def assertMatches(self, count, pattern, mode=None, msg=None):
        
        if not pattern:
            self.fail('no pattern specified')
        
        full_pattern = pattern + r'$'
        if full_pattern[0] != '/':
            full_pattern = r'(?:/[^/]*)*?/' + full_pattern
        
        paths = self.paths
        self.paths = []
        for path in paths:
            if re.match(full_pattern, path):
                if mode is None:
                    test_mode = 0777 if path.endswith('/') else 0666
                else:
                    test_mode = mode
                stat = os.stat(os.path.join(self.root, path.strip('/')))
                self.test.assertEqual(stat.st_mode & 0777, test_mode, 'permissions differ on %r; %o != %o' % (path, stat.st_mode & 0777, test_mode))
                self.matched.add(path)
            else:
                self.paths.append(path)
        self.test.assertEqual(
            count,
            len(paths) - len(self.paths),
            msg or ('found %d, expected %d via %r; %d remain:\n\t' % (len(paths) - len(self.paths), count, pattern, len(self.paths))) + '\n\t'.join(sorted(self.paths))
        )
    
    def assertMatchedAll(self, msg=None):
        self.test.assertFalse(self.paths, msg or ('%d paths remain:\n\t' % len(self.paths)) + '\n\t'.join(sorted(self.paths)))
        
    def assertProject(self):
        self.assertMatches(1, r'/Assets/')
        self.assertMatches(1, r'/SEQ/')
        self.assertMatches(1, r'/\.sgfs-cache\.sqlite')
        self.assertMatches(1, r'/\.sgfs\.yml')
    
    def assertAssetType(self, count):
        self.assertMatches(count,  r'/Assets/(Character|Vehicle)/')
    
    def assertAsset(self, count):
        self.assertMatches(count,  r'/Assets/(Character|Vehicle)/(\1_\d+)/')
        self.assertMatches(count,  r'/Assets/(Character|Vehicle)/(\1_\d+)/\.sgfs\.yml')
    
    def assertAssetTask(self, count, type_, **kwargs):
        self._assertTask(count, r'/Assets/(Character|Vehicle)/(\1_\d+)', type_, **kwargs)
    
    def _assertTask(self, count, base, type_, maya=False, nuke=False, mudbox=False):
        self.assertMatches(count, base + r'/%s/' % type_)
        self.assertMatches(ANY, base + r'/%s/\.sgfs\.yml' % type_)
        self.assertMatches(ANY, base + r'/%s/dailies/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/maya/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/maya/published/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/maya/scenes/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/maya/workspace.mel' % type_)
        self.assertMatches(count if mudbox else 0, base + r'/%s/mudbox/' % type_)
        self.assertMatches(count if mudbox else 0, base + r'/%s/mudbox/published/' % type_)
        self.assertMatches(count if nuke else 0, base + r'/%s/nuke/' % type_)
        self.assertMatches(count if nuke else 0, base + r'/%s/nuke/published/' % type_)
        self.assertMatches(count if nuke else 0, base + r'/%s/nuke/renders/' % type_)
        self.assertMatches(count if nuke else 0, base + r'/%s/nuke/scripts/' % type_)
    
    def assertSequence(self, count):
        self.assertMatches(count, r'/SEQ/(\w{2})/')
        self.assertMatches(count, r'/SEQ/(\w{2})/\.sgfs\.yml')
    
    def assertShot(self, count):
        self.assertMatches(count, r'/SEQ/(\w{2})/\1_\d{3}/')
        self.assertMatches(count, r'/SEQ/(\w{2})/\1_\d{3}/\.sgfs\.yml')
        self.assertMatches(count * 3, r'/SEQ/(\w{2})/\1_\d{3}/(Audio|Plates|Ref)/')
    
    def assertShotTask(self, count, type_, **kwargs):
        self._assertTask(count, r'/SEQ/(\w{2})/\1_\d{3}', type_, **kwargs)
    
    def assertFullStructure(self):
        self.assertProject()
        self.assertAssetType(2)
        self.assertAsset(4)
        self.assertAssetTask(4, 'Anm', maya=True)
        self.assertAssetTask(4, 'Comp', nuke=True)
        self.assertAssetTask(4, 'Model', maya=True, mudbox=True)
        self.assertSequence(2)
        self.assertShot(4)
        self.assertShotTask(4, 'Anm', maya=True)
        self.assertShotTask(4, 'Comp', nuke=True)
        self.assertShotTask(4, 'Model', maya=True, mudbox=True)
        self.assertMatchedAll()
        
    
class Base(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        self.proj_name = 'Test Project ' + mini_uuid()
        proj = fix.Project(self.proj_name)
        seqs = [proj.Sequence(code, project=proj) for code in ('AA', 'BB')]
        shots = [seq.Shot('%s_%03d' % (seq['code'], i), project=proj) for seq in seqs for i in range(1, 3)]
        steps = [fix.find_or_create('Step', code=code, short_name=code) for code in ('Anm', 'Comp', 'Model')]
        assets = [proj.Asset(sg_asset_type=type_, code="%s %d" % (type_, i)) for type_ in ('Character', 'Vehicle') for i in range(1, 3)]
        tasks = [entity.Task(step['code'] + ' something', step=step, entity=entity, project=proj) for step in (steps + steps[-1:]) for entity in (shots + assets)]
        
        self.proj = minimal(proj)
        self.seqs = map(minimal, seqs)
        self.shots = map(minimal, shots)
        self.steps = map(minimal, steps)
        self.tasks = map(minimal, tasks)
        self.assets = map(minimal, assets)

        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session)
        self = None
    
    def pathTester(self):
        return PathTester(self, os.path.join(self.sandbox, self.proj_name.replace(' ', '_')))
        
        

class TestFullStructure(Base):
    
    def test_full_structure(self):
        self.sgfs.create_structure(self.tasks + self.assets, allow_project=True)
        paths = self.pathTester()
        paths.assertFullStructure()

class TestIncrementalStructure(Base):
          
    def test_incremental_structure(self):

        paths = self.pathTester()

        proj = self.session.merge(self.proj)
        proj.fetch('name')
        self.sgfs.create_structure([proj], allow_project=True)
        with paths:
            paths.assertProject()
        
        for seq in self.seqs:
            self.sgfs.create_structure([seq])
            with paths:
                paths.assertSequence(1)
        
        for asset in self.assets:
            self.sgfs.create_structure([asset])
            with paths:
                paths.assertAssetType(ANY)
                paths.assertAsset(1)
        
        for shot in self.shots:
            self.sgfs.create_structure([shot])
            with paths:
                paths.assertShot(1)
        
        self.sgfs.create_structure(self.tasks)
        with paths:
            paths.assertAssetTask(len(self.assets), 'Anm', maya=True)
            paths.assertAssetTask(len(self.assets), 'Comp', nuke=True)
            paths.assertAssetTask(len(self.assets), 'Model', maya=True, mudbox=True)
            paths.assertShotTask(len(self.shots), 'Anm', maya=True)
            paths.assertShotTask(len(self.shots), 'Comp', nuke=True)
            paths.assertShotTask(len(self.shots), 'Model', maya=True, mudbox=True)
            
        root = os.path.join(self.sandbox, self.proj_name.replace(' ', '_'))
        self.assertEqual(1, len(self.sgfs.get_directory_entity_tags(root)))
        self.assertEqual(1, len(self.sgfs.get_directory_entity_tags(root + '/SEQ/AA/AA_001/Anm')))
        self.assertEqual(2, len(self.sgfs.get_directory_entity_tags(root + '/SEQ/AA/AA_001/Model')))



class TestMutatedStructure(Base):
          
    def test_mutated_structure(self):
        
        root = os.path.join(self.sandbox, self.proj_name.replace(' ', '_'))
        
        paths = self.pathTester()

        proj = self.session.merge(self.proj)
        proj.fetch('name')
        self.sgfs.create_structure([proj], allow_project=True)
        with paths:
            paths.assertProject()
        
        for seq in self.seqs:
            self.sgfs.create_structure([seq])
            with paths:
                paths.assertSequence(1)
        
        # Mutate the sequences, and rebuild the cache.
        call(['mv', root + '/SEQ/AA', root + '/SEQ/XX'])
        call(['mv', root + '/SEQ/BB', root + '/SEQ_BB'])
        print '==== MUTATION ===='
        self.sgfs.rebuild_cache(root)
        
        self.sgfs.create_structure(self.shots)
        paths.scan()
        paths.assertMatches(2, r'SEQ/XX/AA_\d+/')
        paths.assertMatches(2, r'SEQ/XX/AA_\d+/\.sgfs\.yml')
        paths.assertMatches(2, r'SEQ_BB/BB_\d+/')
        paths.assertMatches(2, r'SEQ_BB/BB_\d+/\.sgfs\.yml')

        tags = self.sgfs.get_directory_entity_tags(root + '/SEQ/XX/AA_001')
        self.assertEqual(1, len(tags))
        self.assertSameEntity(tags[0]['entity'], self.shots[0])

        tags = self.sgfs.get_directory_entity_tags(root + '/SEQ_BB/BB_001')
        self.assertEqual(1, len(tags))
        self.assertSameEntity(tags[0]['entity'], self.shots[3])


class TestDryRun(Base):
    
    def test_dry_run(self):
        self.sgfs.create_structure(self.tasks + self.assets, dry_run=True)
        paths = self.pathTester()
        paths.assertMatchedAll()


class TestDisallowProject(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        self.proj_name = 'Test Project ' + mini_uuid()
        self.proj = fix.Project(self.proj_name)
        self.sgfs = SGFS(root=self.sandbox, shotgun=fix)
        
    def tearDown(self):
        self.fix.delete_all()
    
    def test_disallow_project(self):
        os.makedirs(os.path.join(self.sandbox, self.proj_name.replace(' ', '_')))
        self.assertRaises(ValueError, self.sgfs.create_structure, [self.proj])
        