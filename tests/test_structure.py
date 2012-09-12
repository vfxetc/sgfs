from __future__ import with_statement

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
        
        for pattern in (r'\._', r'.DS_Store', r'.*\.pyc$'):
            paths = [path for path in paths if not re.match(pattern, path)]
        
        count = len(self.paths)
        for path in paths:
            if path not in self.matched:
                self.paths.append(path)
        print 'PathTester found', len(self.paths) - count, 'new items'
    
    def __enter__(self):
        self.scan()
    
    def __exit__(self, *args):
        self.assertMatchedAll()
        
    def assertMatches(self, count, pattern, msg=None):
        
        if not pattern:
            self.fail('no pattern specified')
        
        full_pattern = pattern + r'$'
        if full_pattern[0] != '/':
            full_pattern = r'(?:/[^/]*)*?/' + full_pattern
        
        paths = self.paths
        self.paths = []
        for path in paths:
            if re.match(full_pattern, path):
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
        self.assertMatches(1,  r'/Assets/')
        self.assertMatches(1, r'/SEQ/')
    
    def assertAssetType(self, count):
        self.assertMatches(count,  r'/Assets/(Model|Texture)/')
    
    def assertAsset(self, count):
        self.assertMatches(count,  r'/Assets/(Model|Texture)/(\1_\d+)/')
    
    def assertAssetTask(self, count, type_, maya=False, nuke=False):
        self._assertTask(count, r'/Assets/(Model|Texture)/(\1_\d+)', type_, maya=maya, nuke=nuke)
    
    def _assertTask(self, count, base, type_, maya, nuke):
        self.assertMatches(count, base + r'/%s/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/scenes/' % type_)
        self.assertMatches(count if maya else 0, base + r'/%s/workspace.mel' % type_)
        self.assertMatches(count if nuke else 0, base + r'/%s/scripts/' % type_)
    
    def assertSequence(self, count):
        self.assertMatches(count, r'/SEQ/(\w{2})/')
    
    def assertShot(self, count):
        self.assertMatches(count, r'/SEQ/(\w{2})/\1_\d{3}/')
        self.assertMatches(count * 3, r'/SEQ/(\w{2})/\1_\d{3}/(Audio|Plates|Ref)/')
    
    def assertShotTask(self, count, type_, maya=False, nuke=False):
        self._assertTask(count, r'/SEQ/(\w{2})/\1_\d{3}', type_, maya=maya, nuke=nuke)
    
    def assertFullStructure(self):
        self.assertProject()
        self.assertAssetType(2)
        self.assertAsset(4)
        self.assertAssetTask(4, 'Anm', maya=True, nuke=False)
        self.assertAssetTask(4, 'Comp', maya=False, nuke=True)
        self.assertAssetTask(4, 'Model', maya=True, nuke=False)
        self.assertSequence(2)
        self.assertShot(4)
        self.assertShotTask(4, 'Anm', maya=True, nuke=False)
        self.assertShotTask(4, 'Comp', maya=False, nuke=True)
        self.assertShotTask(4, 'Model', maya=True, nuke=False)
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
        assets = [proj.Asset(sg_asset_type=type_, code="%s %d" % (type_, i)) for type_ in ('Model', 'Texture') for i in range(1, 3)]
        tasks = [entity.Task(step['code'] + ' something', step=step, entity=entity, project=proj) for step in steps for entity in (shots + assets)]
        
        self.proj = minimal(proj)
        self.seqs = map(minimal, seqs)
        self.shots = map(minimal, shots)
        self.steps = map(minimal, steps)
        self.tasks = map(minimal, tasks)
        self.assets = map(minimal, assets)

        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session)
        self = None
    
    def create(self, entities):
        merged = [self.session.merge(x) for x in entities]
        context = self.sgfs.context_from_entities(merged)
        schema = self.sgfs.schema('v1')
        structure = schema.structure(context)
        structure.create(self.sandbox, verbose=True)
    
    def pathTester(self):
        return PathTester(self, os.path.join(self.sandbox, self.proj_name.replace(' ', '_')))
        
        

class TestFullStructure(Base):
    
    def test_full_structure(self):
        self.create(self.tasks + self.assets)
        paths = self.pathTester()
        paths.assertFullStructure()

class TestIncrementalStructure(Base):
          
    def test_incremental_structure(self):
        proj = self.session.merge(self.proj)
        proj.fetch('name')

        paths = self.pathTester()
        paths.assertMatchedAll()

        self.create([proj])
        with paths:
            paths.assertProject()
        
        for seq in self.seqs:
            self.create([seq])
            with paths:
                paths.assertSequence(1)
        
        for asset in self.assets:
            self.create([asset])
            with paths:
                paths.assertAssetType(ANY)
                paths.assertAsset(1)
        
        for shot in self.shots:
            self.create([shot])
            with paths:
                paths.assertShot(1)
        
        self.create(self.tasks)
        with paths:
            paths.assertAssetTask(len(self.assets), 'Anm', maya=True, nuke=False)
            paths.assertAssetTask(len(self.assets), 'Comp', maya=False, nuke=True)
            paths.assertAssetTask(len(self.assets), 'Model', maya=True, nuke=False)
            paths.assertShotTask(len(self.shots), 'Anm', maya=True, nuke=False)
            paths.assertShotTask(len(self.shots), 'Comp', maya=False, nuke=True)
            paths.assertShotTask(len(self.shots), 'Model', maya=True, nuke=False)
        
       