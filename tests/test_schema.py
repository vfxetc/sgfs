import os
from pprint import pprint
from subprocess import call
from unittest import TestCase
import itertools

from sgsession import fixtures

from sgfs import SGFS


def setUpModule():
    fixtures.setup_tasks()


class TestSchema(TestCase):
    
    def setUp(self):
        self.sgfs = SGFS(root=fixtures.root, shotgun=fixtures.sg)
        
    def test_loading(self):
        
        schema = self.sgfs.schema('testing')
        schema.pprint()
        
        self.assertEqual(schema.entity_type, 'Project')
        self.assertEqual(len(schema.children), 2)
        
        asset = schema.children['Asset']
        self.assertEqual(asset.entity_type, 'Asset')
        self.assertEqual(len(asset.children), 1)
        
        atask = asset.children['Task']
        self.assertEqual(atask.entity_type, 'Task')
        self.assertEqual(len(atask.children), 0)
        
        seq = schema.children['Sequence']
        self.assertEqual(seq.entity_type, 'Sequence')
        self.assertEqual(len(seq.children), 1)
        
        shot = seq.children['Shot']
        self.assertEqual(shot.entity_type, 'Shot')
        self.assertEqual(len(shot.children), 1)
        
        stask = shot.children['Task']
        self.assertEqual(stask.entity_type, 'Task')
        self.assertEqual(len(stask.children), 0)
        
    def test_structure(self):
        
        entities = [self.sgfs.session.merge(x) for x in fixtures.tasks[:]]
        self.sgfs.session.fetch_heirarchy(entities)
        
        print 'ENTITIES'
        entities[0].project().pprint(backrefs=3)
        print
        
        print 'CONTEXT'
        context = self.sgfs.context_from_entities(entities)
        context.pprint()
        print

        print 'SCHEMA'
        schema = self.sgfs.schema('testing')
        schema.pprint()
        print
        
        print 'STRUCTURE'
        structure = schema.structure(context)
        structure.pprint()
        print
        
        print 'CALLS'
        structure.preview('./project')
        print
        
        