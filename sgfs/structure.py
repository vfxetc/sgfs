import os

from . import utils


def _get_or_eval(namespace, name, default=None):
    if name in namespace:
        return namespace[name]
    expr_name = name + '_expr'
    if expr_name in namespace:
        return utils.eval_expr_or_func(namespace[expr_name], namespace)
    return default


class Structure(object):
    
    def __init__(self, namespace, children):
        self.children = children
        name = _get_or_eval(namespace, 'name', '')
        path = _get_or_eval(namespace, 'path', '')
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
    
    def __init__(self, namespace, children, template=None):
        super(Directory, self).__init__(namespace, children)
        


class Entity(Directory):
    pass


class Include(Structure):
    pass


class File(Structure):
    pass


