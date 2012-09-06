from unittest import TestCase
import time
import os
import itertools
import datetime

import shotgun_api3_registry


sg = None
project = {}
sequences = []
shots = []
tasks = []


def mini_uuid():
    return os.urandom(4).encode('hex')


def setUpModule():
    
    global sg
    sg = shotgun_api3_registry.connect(name='sgfs.tests', server='testing')
    
    project.update(sg.create('Project', dict(
        name='test_project_%s' % (datetime.datetime.now().strftime('%Y%m%d_%H%M%S')),
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
    
    # Delete all entities.
    if not sg:
        return
    sg.batch([
        {'request_type': 'delete', 'entity_type': x['type'], 'entity_id': x['id']}
        for x in itertools.chain(tasks, shots, sequences, [project])
        if x
    ])


class TestContext(TestCase):
    
    def test_true(self):
        self.assert_(True)
    