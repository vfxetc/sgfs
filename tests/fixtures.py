from subprocess import call
import datetime
import os

import shotgun_api3_registry


sg = None
project = {}
sequences = []
shots = []
tasks = []

timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
root = os.path.join(os.path.dirname(__file__), 'root_' + timestamp)

def mini_uuid():
    return os.urandom(4).encode('hex')


def setup_sg():
    global sg
    if not sg:
        sg = shotgun_api3_registry.connect(name='sgfs.tests', server='testing')


def setup_project():
    setup_sg()
    if not project:
        if not os.path.exists(root):
            os.makedirs(root)
        project.update(sg.create('Project', dict(
            name='test_project_%s' % (timestamp),
            sg_code='test_project_%s' % (timestamp), # Only on test server.
            sg_description='For unit testing.',
        )))


def setup_sequences():
    setup_project()
    if not sequences:
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
            
            
    

def tear_down():
    
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

