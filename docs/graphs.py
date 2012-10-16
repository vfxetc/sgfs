import os
import datetime

from sgmock import Shotgun, ShotgunError, Fault, Fixture
from sgsession import Session, Entity
from sgfs import SGFS, Schema, Context, Structure


def mini_uuid():
    return os.urandom(4).encode('hex')

def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

def minimal(entity):
    return dict(type=entity['type'], id=entity['id'])


sandbox = os.path.abspath(os.path.join(__file__, '..', 'sandbox', timestamp()))
os.makedirs(sandbox)
    
    
def graph(func):
    path = os.path.abspath(os.path.join(__file__, '..', 'graphs', func.__name__ + '.dot'))
    print path
    output = func()
    with open(path, 'w') as fh:
        fh.write('digraph %s {\n' % func.__name__)
        fh.write('graph [rankdir="LR"]\n')
        fh.write('node [fontsize=10]\n')
        fh.write(output)
        fh.write('}\n')
    return func


class LargeFixture():
    
    def __init__(self):
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
        self.sgfs = SGFS(root=sandbox, session=self.session)

@graph
def linear_context():
    fix = LargeFixture()
    task = fix.session.merge(fix.tasks[0])
    ctx = fix.sgfs.context_from_entities([task])
    return ctx.dot()

@graph
def task_forked_context():
    fix = LargeFixture()
    tasks = fix.session.merge(fix.tasks[:2])
    ctx = fix.sgfs.context_from_entities(tasks)
    return ctx.dot()
        