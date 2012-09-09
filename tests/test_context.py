from pprint import pprint
from subprocess import call
from unittest import TestCase
import itertools

from sgsession import fixtures

from sgfs import SGFS


def setUpModule():
    fixtures.setup_tasks()


class TestContext(TestCase):
    
    def setUp(self):
        self.sgfs = SGFS(root=fixtures.root, shotgun=fixtures.sg)
        
    def test_context_from_entities(self):
        
        shots = [self.sgfs.session.merge(x) for x in fixtures.tasks]
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
        
        shots = [self.sgfs.session.merge(x) for x in fixtures.tasks]
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
        
        