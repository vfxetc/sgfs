import os

import yaml

from . import utils


def _get_or_eval(globals_, locals_, name, default=None):
    for namespace in (locals_, globals_):
        if name in namespace:
            return namespace[name]
        expr_name = name + '_expr'
        if expr_name in namespace:
            return utils.eval_expr_or_func(namespace[expr_name], globals_, locals_)
    return default


class Structure(object):
    
    def __init__(self, globals_, locals_, children):
        
        self.children = children
        
        name = str(_get_or_eval(globals_, locals_, 'name', ''))
        path = str(_get_or_eval(globals_, locals_, 'path', ''))
        self.name = os.path.join(path, name)
    
    def pprint(self, depth=0):
        print '%s%s %r at 0x%x' % (
            '\t' * depth,
            self.__class__.__name__,
            self.name,
            id(self)
        ),
        if not self.children:
            print
            return
        
        print '{'
        for child in self.children:
            child.pprint(depth + 1)
        print '\t' * depth + '}'
    


class Directory(Structure):
    
    def __init__(self, globals_, locals_, children, template=None):
        super(Directory, self).__init__(globals_, locals_, children)
        
        if template:
            names = os.listdir(template)
            paths = [os.path.join(template, name) for name in names if not (
                name.startswith('._') or
                name == '.sgfs-ignore'
            )]
            for special in [x for x in paths if x.endswith('.yml')]:
                config = yaml.load(open(special).read()) or {}
                local_template = os.path.splitext(special)[0]
                if os.path.exists(local_template):
                    config['template'] = local_template
                    paths.remove(local_template)
                    


class Entity(Directory):
    pass


class Include(Structure):
    pass


class File(Structure):
    pass


