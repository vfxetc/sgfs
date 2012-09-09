from pprint import pprint
from subprocess import call
from unittest import TestCase
import itertools

from sgfs import SGFS

from . import fixtures


def setUpModule():
    # fixtures.setup_tasks()
    globals().update(fixtures.__dict__)


class TestSchema(TestCase):
    
    def setUp(self):
        self.sgfs = SGFS(root=root, shotgun=sg)
        
    def test_structure(self):
        
        schema = self.sgfs.schema('testing')
        print schema
        
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
        
        