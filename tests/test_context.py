from pprint import pprint
from subprocess import call
from unittest import TestCase
import datetime
import itertools
import os
import time

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.utils import parent


timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
root = os.path.join(os.path.dirname(__file__), 'root_' + timestamp)

sg = None
project = {}
sequences = []
shots = []
tasks = []



def mini_uuid():
    return os.urandom(4).encode('hex')


def setUpModule():
    
    if not os.path.exists(root):
        os.makedirs(root)
    
    global sg
    sg = shotgun_api3_registry.connect(name='sgfs.tests', server='testing')
    
    project.update(sg.create('Project', dict(
        name='test_project_%s' % (timestamp),
        sg_code='test_project_%s' % (timestamp), # Only on test server.
        sg_description='For unit testing.',
    )))
    
    for seq_code in ('AA', 'BB'):
        
        sequences.append(sg.create('Sequence', dict(
            code=seq_code,
            project=project,
        )))
        
        for shot_i in range(1, 3):
            shots.append(sg.create('Shot', dict(
                description='Test Shot %s-%s' % (seq_code, shot_i),
                code='%s_%03d' % (seq_code, shot_i),
                sg_sequence=sequences[-1],
                project=project,
            )))
            
            
    

def tearDownModule():
    
    return
    
    if os.path.exists(root):
        call(['rm', '-rf', root])
    
    # Delete all entities.
    if not sg:
        return
    sg.batch([
        {'request_type': 'delete', 'entity_type': x['type'], 'entity_id': x['id']}
        for x in itertools.chain(tasks, shots, sequences, [project])
        if x
    ])


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
        
        