import os
import datetime
import types

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
    

def make_graph_decorator(dir_name):
    def graph(func):
        print dir_name, func.__name__
        dir_path = os.path.abspath(os.path.join(__file__, '..', '_graphs', dir_name))
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        base = os.path.join(dir_path, func.__name__)
        output = func()
    
        if not isinstance(output, (list, tuple, basestring, types.GeneratorType)):
            output = output.dot()
        if isinstance(output, basestring):
            output = [output]
    
        for i, output in enumerate(output):
            path = '%s.%d.dot' % (base, i)
            print '\t' + path
            with open(path, 'w') as fh:
                fh.write('digraph %s {\n' % func.__name__)
                fh.write('graph [rankdir="LR", dpi=60]\n')
                fh.write('node [fontsize=14]\n')
                fh.write(output)
                fh.write('}\n')
        return func
    return graph


class LargeFixture():
    
    def __init__(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        proj = fix.Project('Example Project')
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

if __name__ == '__main__':
    base_namespace = dict(globals())
    dir_name = os.path.abspath(os.path.join(__file__, '..', '_graphs'))
    for file_name in os.listdir(dir_name):
        if not file_name.endswith('.py'):
            continue
        path = os.path.join(dir_name, file_name)
        namespace = dict(base_namespace)
        base_name = os.path.basename(os.path.splitext(file_name)[0])
        namespace['graph'] = make_graph_decorator(base_name)
        execfile(path, namespace)


        