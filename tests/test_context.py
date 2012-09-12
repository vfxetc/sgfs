from common import *

import itertools

from sgfs import SGFS


class TestContext(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        proj = fix.Project(mini_uuid())
        seqs = [proj.Sequence(code, project=proj) for code in ('AA', 'BB')]
        shots = [seq.Shot('%s_%03d' % (seq['code'], i), project=proj) for seq in seqs for i in range(1, 3)]
        steps = [fix.find_or_create('Step', code=code, short_name=code) for code in ('Anm', 'Comp', 'Model')]
        tasks = [shot.Task(step['code'] + ' something', step=step, entity=shot, project=proj) for step in steps for shot in shots]
        
        self.proj = minimal(proj)
        self.seqs = [minimal(x) for x in seqs]
        self.shots = [minimal(x) for x in shots]
        self.steps = [minimal(x) for x in steps]
        self.tasks = [minimal(x) for x in tasks]

        self.root = os.path.join('scratch', mini_uuid())
        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.root, session=self.session)
        self.session = self.sgfs.session
        
    def test_context_from_entities(self):
        
        shots = [self.session.merge(x) for x in self.tasks]
        shots[0].pprint()
        print
        
        ctx = self.sgfs.context_from_entities([shots[0]])
        ctx.pprint()
        print
        
        self.assert_(ctx.is_linear)
        self.assertEqual(len(ctx.linear_base), 4)
        self.assertEqual(len(list(ctx.iter_leafs())), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Project')))), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Sequence')))), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Shot')))), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Task')))), 1)
        
        ctx = self.sgfs.context_from_entities(shots)
        ctx.pprint()
        print
        
        self.assert_(not ctx.is_linear)
        self.assertEqual(len(ctx.linear_base), 1)
        self.assertEqual(len(list(ctx.iter_leafs())), 12)
        self.assertEqual(len(list(ctx.iter_by_type(('Project')))), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Sequence')))), 2)
        self.assertEqual(len(list(ctx.iter_by_type(('Shot')))), 4)
        self.assertEqual(len(list(ctx.iter_by_type(('Task')))), 12)
            
    def test_linearize(self):
        
        shots = [self.session.merge(x) for x in self.tasks]
        ctx = self.sgfs.context_from_entities(shots)
        ctx.pprint()
        print
        
        self.assert_(not ctx.is_linear)
        self.assertEqual(len(ctx.linear_base), 1)
        self.assertEqual(len(list(ctx.iter_leafs())), 12)
        self.assertEqual(len(list(ctx.iter_by_type(('Project')))), 1)
        self.assertEqual(len(list(ctx.iter_by_type(('Sequence')))), 2)
        self.assertEqual(len(list(ctx.iter_by_type(('Shot')))), 4)
        self.assertEqual(len(list(ctx.iter_by_type(('Task')))), 12)
        
        linearized = list(ctx.iter_linearized())
        for lin in linearized:
            lin.pprint()
        
        self.assertEqual(len(linearized), 12)
        self.assertEqual(
            set(list(x.iter_leafs())[0].entity for x in linearized),
            set(x.entity for x in ctx.iter_leafs()),
        )
        
        