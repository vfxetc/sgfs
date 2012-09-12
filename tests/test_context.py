from common import *


class TestContext(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        proj = fix.Project('Test Project ' + mini_uuid())
        seqs = [proj.Sequence(code, project=proj) for code in ('AA', 'BB')]
        shots = [seq.Shot('%s_%03d' % (seq['code'], i), project=proj) for seq in seqs for i in range(1, 3)]
        steps = [fix.find_or_create('Step', code=code, short_name=code) for code in ('Anm', 'Comp', 'Model')]
        tasks = [shot.Task(step['code'] + ' something', step=step, entity=shot, project=proj) for step in steps for shot in shots]
                
        self.proj = minimal(proj)
        self.seqs = map(minimal, seqs)
        self.shots = map(minimal, shots)
        self.steps = map(minimal, steps)
        self.tasks = map(minimal, tasks)

        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session)
        
    def test_context_from_single_task(self):
        
        task = self.session.merge(self.tasks[0])
        ctx = self.sgfs.context_from_entities([task])
        
        self.assertTrue(ctx.is_linear)
        self.assertEqual(len(ctx.linear_base), 4)
        
        self.assertEqual(len(list(ctx.iter_leafs())), 1)
        self.assertSameEntity(next(ctx.iter_leafs()).entity, self.tasks[0])
        
        self.assertEqual(len(list(ctx.iter_by_type('Project'))), 1)
        self.assertSameEntity(next(ctx.iter_by_type('Project')).entity, self.proj)
        
        self.assertEqual(len(list(ctx.iter_by_type('Sequence'))), 1)
        self.assertSameEntity(next(ctx.iter_by_type('Sequence')).entity, self.seqs[0])
        
        self.assertEqual(len(list(ctx.iter_by_type('Shot'))), 1)
        self.assertSameEntity(next(ctx.iter_by_type('Shot')).entity, self.shots[0])
        
        self.assertEqual(len(list(ctx.iter_by_type('Task'))), 1)
        self.assertSameEntity(next(ctx.iter_by_type('Task')).entity, self.tasks[0])
        
        self.assertSameEntity(ctx.entity, self.proj)
        self.assertSameEntity(ctx.children[0].entity, self.seqs[0])
        self.assertSameEntity(ctx.children[0].children[0].entity, self.shots[0])
        self.assertSameEntity(ctx.children[0].children[0].children[0].entity, self.tasks[0])
    
    def test_context_from_multiple_tasks(self):
        
        tasks = [self.session.merge(x) for x in self.tasks]
        ctx = self.sgfs.context_from_entities(tasks)
        
        self.assertFalse(ctx.is_linear)
        self.assertEqual(len(ctx.linear_base), 1)
        self.assertEqual(len(list(ctx.iter_leafs())), 12)
        self.assertEqual(len(list(ctx.iter_by_type('Project'))), 1)
        self.assertEqual(len(list(ctx.iter_by_type('Sequence'))), 2)
        self.assertEqual(len(list(ctx.iter_by_type('Shot'))), 4)
        self.assertEqual(len(list(ctx.iter_by_type('Task'))), 12)
            
    def test_linearize(self):
        
        tasks = [self.session.merge(x) for x in self.tasks]
        ctx = self.sgfs.context_from_entities(tasks)
        
        linearized = list(ctx.iter_linearized())
        for lin in linearized:
            lin.pprint()
        
        self.assertEqual(len(linearized), 12)
        self.assertEqual(
            set(list(x.iter_leafs())[0].entity for x in linearized),
            set(x.entity for x in ctx.iter_leafs()),
        )
        
        