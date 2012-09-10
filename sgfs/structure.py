import os
import fnmatch

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
    
    @classmethod
    def from_config(cls, globals_, locals_, default_type=None):
        
        type_ = locals_.get('type', default_type)
        
        constructor = {
            'directory': Directory,
            'entity': Entity,
            'include': Include,
            'file': File,
        }.get(type_)
        
        if not constructor:
            raise ValueError('could not determine type')
            
        return constructor(globals_, locals_)
        
    def __init__(self, globals_, locals_, children=None):
        
        self.children = children or []
        
        name = str(_get_or_eval(globals_, locals_, 'name', ''))
        path = str(_get_or_eval(globals_, locals_, 'path', ''))
        self.name = os.path.join(path, name)
        self.file = locals_.get('__file__')
        self.file = os.path.basename(self.file) if self.file is not None else None
    
    def _repr_headline(self):
        return '%s %r at 0x%x from %r' % (
            self.__class__.__name__,
            self.name,
            id(self),
            self.file,
        )
    
    def pprint(self, depth=0):
        print '\t' * depth + self._repr_headline()
        for child in self.children:
            child.pprint(depth + 1)
    


class Directory(Structure):
    
    def __init__(self, globals_, locals_, children=None, template=None):
        super(Directory, self).__init__(globals_, locals_, children)
        
        if template:
            
            # Build up the ignore list.
            ignore = ['._*', '.sgfs-ignore']
            ignore_file = os.path.join(template, '.sgfs-ignore')
            if os.path.exists(ignore_file):
                for line in open(ignore_file):
                    line = line.strip()
                    if not line or line[0] == '#':
                        continue
                    ignore.append(ignore_file)
            
            # List the directory and apply the ignore list.
            names = os.listdir(template)
            names = [x for x in names if not any(fnmatch.fnmatch(x, pattern) for pattern in ignore)]
            paths = [os.path.join(template, name) for name in names]
            
            # Find anything special, and turn it into children.
            for special in [x for x in paths if x.endswith('.yml')]:
                
                config = yaml.load(open(special).read()) or {}
                config['__file__'] = special
                local_template = os.path.splitext(special)[0]
                
                if os.path.exists(local_template):
                    config['template'] = local_template
                    paths.remove(local_template)
                
                self.children.append(Structure.from_config(globals_, config, default_type='directory'))
        
            # Generic files/directories.
            for path in [x for x in paths if not x.endswith('.yml')]:
                default_type = 'directory' if os.path.isdir(path) else 'file'
                self.children.append(Structure.from_config(
                    globals_,
                    {'path': '', 'name': os.path.basename(path)},
                    default_type=default_type,
                ))
                    
        self.children.sort(key=lambda x: x.name)
    
    def _repr_headline(self):
        return self.name + '/'
                    


class Entity(Directory):
    
    def __init__(self, globals_, locals_, *args, **kwargs):
        super(Entity, self).__init__(globals_, locals_, *args, **kwargs)
        self.entity = globals_['self']
    
    def _repr_headline(self):
        return '%s/ <- %s %s' % (self.name, self.entity['type'], self.entity['id']) 
    


class Include(Structure):
    
    def _repr_headline(self):
        return '<%s %s>' % (self.__class__.__name__, self.file)


class File(Structure):
    pass


