from pprint import pprint
from subprocess import call
from unittest import TestCase
import itertools

from sgfs import SGFS

from . import fixtures
fixtures.setup_sequences()
from .fixtures import *


class TestContext(TestCase):
    
    def setUp(self):
        self.sgfs = SGFS(root=root, shotgun=sg)
        
    def test_fetch_single_parent(self):
        resolved = self.sgfs._fetch_entity_parents([shots[-1]])
        shot = resolved[0]
        
        pprint(shot)
        pprint(parent(shot))
        pprint(parent(parent(shot)))
        
        self.assertEqual(shot['id'], shots[-1]['id'])
        self.assertEqual(parent(shot)['id'], sequences[-1]['id'])
        self.assertEqual(parent(parent(shot))['id'], project['id'])
    
    def test_fetch_multiple_parent(self):
        resolved = self.sgfs._fetch_entity_parents(shots)
        
        for i, shot in enumerate(resolved):
            # Shots are still in the same order.
            self.assertEqual(shot['id'], shots[i]['id'])
            # They map to the right projects.
            self.assertEqual(parent(parent(shot))['id'], project['id'])
        
        self.assertEqual(parent(resolved[0])['id'], sequences[0]['id'])
        self.assertEqual(parent(resolved[1])['id'], sequences[0]['id'])
        self.assertEqual(parent(resolved[2])['id'], sequences[1]['id'])
        self.assertEqual(parent(resolved[3])['id'], sequences[1]['id'])
        
        for shot in resolved[1:]:
            self.assert_(parent(parent(shot)) is parent(parent(resolved[0])))
        
        self.assert_(parent(resolved[0]) is parent(resolved[1]))
        self.assert_(parent(resolved[0]) is not parent(resolved[2]))
        self.assert_(parent(resolved[2]) is parent(resolved[3]))
        
        
        
        
        