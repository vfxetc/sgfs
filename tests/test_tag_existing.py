from common import *


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


class TestTagExistingV1(Base):
    
    def test_tag_existing_v1(self):
        
        proj = self.session.merge(self.proj)
        seqs = self.session.merge(self.seqs)
        shots = self.session.merge(self.shots)
        tasks = self.session.merge(self.tasks)
        
        root = os.path.abspath(os.path.join(self.sandbox, self.proj_name.replace(' ', '_')))
        for path in '''
            SEQ/AA/AA_001/Anm
            SEQ/AA/AA_001/Model
            SEQ/AA/AA_002
            SEQ/BB
        '''.strip().split():
            os.makedirs(os.path.join(root, path))
        
        self.assertIsNone(self.sgfs.path_cache(proj))
        
        self.sgfs.tag_existing(tasks, schema_name='v1', verbose=True)
        
        cache = self.sgfs.path_cache(proj)
        
        self.assertEqual(8, len(cache))
        print cache.keys()
        self.assertEqual(cache.get(proj), root)
        self.assertEqual(cache.get(seqs[0]), root + '/SEQ/AA')
        self.assertEqual(cache.get(shots[0]), root + '/SEQ/AA/AA_001')
        self.assertEqual(cache.get(tasks[0]), root + '/SEQ/AA/AA_001/Anm')
        self.assertEqual(cache.get(tasks[16]), root + '/SEQ/AA/AA_001/Model')
        self.assertEqual(cache.get(tasks[24]), root + '/SEQ/AA/AA_001/Model')
        self.assertEqual(cache.get(shots[1]), root + '/SEQ/AA/AA_002')
        self.assertEqual(cache.get(seqs[1]), root + '/SEQ/BB')
        