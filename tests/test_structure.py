import re

from common import *


class PathTester(object):
    
    def __init__(self, test, root):
        self.test = test
        self.root = root
        self.paths = []
        
        for dir_name, dir_names, file_names in os.walk(root):
            for name in dir_names:
                path = '/' + os.path.relpath(os.path.join(dir_name, name), root) + '/'
                self.paths.append(path)
            for name in file_names:
                path = '/' + os.path.relpath(os.path.join(dir_name, name), root)
                self.paths.append(path)
        
        for pattern in (r'\._', r'.DS_Store', r'.*\.pyc$'):
            self.ignore(pattern)
    
    def ignore(self, pattern):
        self.paths = [path for path in self.paths if not re.match(pattern, path)]
    
    def assertMatches(self, count, pattern, msg=None):
        
        if not pattern:
            self.fail('no pattern specified')
        
        full_pattern = pattern + r'$'
        if full_pattern[0] != '/':
            full_pattern = r'(?:/[^/]*)*?/' + full_pattern
        
        paths = self.paths
        self.paths = []
        for path in paths:
            if not re.match(full_pattern, path):
                self.paths.append(path)
        self.test.assertEqual(
            count,
            len(paths) - len(self.paths),
            msg or ('found %d, expected %d via %r; %d remain:\n\t' % (len(paths) - len(self.paths), count, pattern, len(self.paths))) + '\n\t'.join(sorted(self.paths))
        )
    
    def assertMatchedAll(self, msg=None):
        self.test.assertFalse(self.paths, msg or ('%d paths remain:\n\t' % len(self.paths)) + '\n\t'.join(sorted(self.paths)))
    
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
    
    def pathTester(self, path):
        return PathTester(self, path)


class TestFullStructure(Base):
    
    def test_full_structure(self):
        
        tasks = [self.session.merge(x) for x in self.tasks]
        assets = [self.session.merge(x) for x in self.assets]
        context = self.sgfs.context_from_entities(tasks + assets)
        schema = self.sgfs.schema('v1')
        structure = schema.structure(context)
        structure.create(self.sandbox)
        
        paths = self.pathTester(os.path.join(self.sandbox, self.proj_name.replace(' ', '_')))
        
        paths.assertMatches(1,  r'/Assets/')
        paths.assertMatches(2,  r'/Assets/(Model|Texture)/')
        paths.assertMatches(4,  r'/Assets/(Model|Texture)/(\1_\d+)/')
        paths.assertMatches(12, r'/Assets/(Model|Texture)/(\1_\d+)/(Anm|Comp|Model)/')
        paths.assertMatches(8,  r'/Assets/(Model|Texture)/(\1_\d+)/(Anm|Model)/scenes/')
        paths.assertMatches(8,  r'/Assets/(Model|Texture)/(\1_\d+)/(Anm|Model)/workspace.mel')
        paths.assertMatches(4,  r'/Assets/(Model|Texture)/(\1_\d+)/(Comp)/scripts/')
        
        paths.assertMatches(1, r'/SEQ/')
        paths.assertMatches(2, r'/SEQ/(\w{2})/')
        paths.assertMatches(4, r'/SEQ/(\w{2})/\1_\d{3}/')
        paths.assertMatches(12, r'/SEQ/(\w{2})/\1_\d{3}/(Audio|Plates|Ref)/')
        paths.assertMatches(12, r'/SEQ/(\w{2})/\1_\d{3}/(Anm|Comp|Model)/')
        paths.assertMatches(8,  r'/SEQ/(\w{2})/\1_\d{3}/(Anm|Model)/scenes/')
        paths.assertMatches(8,  r'/SEQ/(\w{2})/\1_\d{3}/(Anm|Model)/workspace.mel')
        paths.assertMatches(4,  r'/SEQ/(\w{2})/\1_\d{3}/(Comp)/scripts/')
        
        paths.assertMatchedAll()
        