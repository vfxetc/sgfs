from common import *


class TestContextFromPath(TestCase):
    
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
    
    def create(self, entities):
        merged = [self.session.merge(x) for x in entities]
        context = self.sgfs.context_from_entities(merged)
        schema = self.sgfs.schema('v1')
        structure = schema.structure(context)
        structure.create(self.sandbox, verbose=True)
    
    def test_context_from_path(self):
        
        self.create(self.tasks)
        
        root = os.path.join(self.sandbox, self.proj_name.replace(' ', '_'))
        
        for path in ('', 'Assets', 'SEQ'):
            sgfs = SGFS(root=self.sandbox, session=self.session)
            context = sgfs.context_from_path(os.path.join(root, path))
            self.assertIsNotNone(context)
            context.pprint()
            self.assertTrue(context.is_linear)
            self.assertEqual(1, len(context.linear_base))
            self.assertSameEntity(context.entity, self.proj)
            
            entities = sgfs.entities_from_path(os.path.join(root, path))
            self.assertEqual(1, len(entities))
            self.assertSameEntity(entities[0], self.proj)
        
        sgfs = SGFS(root=self.sandbox, session=self.session)
        context = sgfs.context_from_path(root + '/SEQ/AA')
        self.assertIsNotNone(context)
        context.pprint()
        self.assertTrue(context.is_linear)
        self.assertEqual(2, len(context.linear_base))
        self.assertSameEntity(context.entity, self.proj)
        self.assertSameEntity(context.children[0].entity, self.seqs[0])
        
        entities = sgfs.entities_from_path(root + '/SEQ/AA')
        self.assertEqual(1, len(entities))
        self.assertSameEntity(entities[0], self.seqs[0])
        
        sgfs = SGFS(root=self.sandbox, session=self.session)
        context = sgfs.context_from_path(root + '/SEQ/AA/AA_001')
        self.assertIsNotNone(context)
        context.pprint()
        self.assertTrue(context.is_linear)
        self.assertEqual(3, len(context.linear_base))
        self.assertSameEntity(context.entity, self.proj)
        self.assertSameEntity(context.children[0].entity, self.seqs[0])
        self.assertSameEntity(context.children[0].children[0].entity, self.shots[0])
        
        entities = sgfs.entities_from_path(root + '/SEQ/AA/AA_001')
        self.assertEqual(1, len(entities))
        self.assertSameEntity(entities[0], self.shots[0])
        
        sgfs = SGFS(root=self.sandbox, session=self.session)
        context = sgfs.context_from_path(root + '/SEQ/AA/AA_001/Anm')
        self.assertIsNotNone(context)
        context.pprint()
        self.assertTrue(context.is_linear)
        self.assertEqual(4, len(context.linear_base))
        self.assertSameEntity(context.entity, self.proj)
        self.assertSameEntity(context.children[0].entity, self.seqs[0])
        self.assertSameEntity(context.children[0].children[0].entity, self.shots[0])
        self.assertSameEntity(context.children[0].children[0].children[0].entity, self.tasks[0])
        
        entities = sgfs.entities_from_path(root + '/SEQ/AA/AA_001/Anm')
        self.assertEqual(1, len(entities))
        self.assertSameEntity(entities[0], self.tasks[0])
        
        sgfs = SGFS(root=self.sandbox, session=self.session)
        context = sgfs.context_from_path(root + '/SEQ/AA/AA_001/Model')
        self.assertIsNotNone(context)
        context.pprint()
        self.assertFalse(context.is_linear)
        self.assertEqual(3, len(context.linear_base))
        self.assertSameEntity(context.entity, self.proj)
        self.assertSameEntity(context.children[0].entity, self.seqs[0])
        self.assertSameEntity(context.children[0].children[0].entity, self.shots[0])
        self.assertSameEntity(context.children[0].children[0].children[0].entity, self.tasks[3])
        self.assertSameEntity(context.children[0].children[0].children[1].entity, self.tasks[4])
        
        entities = sgfs.entities_from_path(root + '/SEQ/AA/AA_001/Model')
        self.assertEqual(2, len(entities))
        self.assertSameEntity(entities[0], self.tasks[3])
        self.assertSameEntity(entities[0], self.tasks[4])
        
        
        
        
        
        

       