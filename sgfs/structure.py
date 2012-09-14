import os
import fnmatch
import subprocess

import yaml

from . import utils
from . import processor


def _namespace_from_context(context, base=None):
    namespace = dict(base or {})
    namespace['self'] = context.entity
    head = context
    while head:
        namespace[head.entity['type']] = head.entity
        head = head.parent
    return namespace


class Structure(object):
    
    @classmethod
    def from_context(cls, context, config):
        
        type_ = config.get('type')
        constructor = {
            'directory': Directory,
            'entity': Entity,
            'file': File,
            'include': Include,
        }.get(type_)
        if not constructor:
            raise ValueError('could not determine type')
        
        if constructor._should_construct(context, config):
            return constructor(context, config)
        
    @classmethod
    def _should_construct(cls, context, config):
        if 'condition' not in config:
            return True
        return bool(utils.eval_expr_or_func(
            config['condition'],
            _namespace_from_context(context, config),
        ))
    
    def __init__(self, context, config):
        
        self.context = context
        self.config = config
        
        self.name = str(self._get_or_eval('name', ''))
        self.children = []
    
    def _get_or_eval(self, name, default=None):
        if name in self.config:
            return self.config[name]
        expr_name = name + '_expr'
        if expr_name in self.config:
            return utils.eval_expr_or_func(
                self.config[expr_name],
                _namespace_from_context(self.context, self.config),
            )
        return default
        
    def _repr_headline(self):
        return '%s %r at 0x%x' % (
            self.__class__.__name__,
            self.name,
            id(self),
        )
    
    def pprint(self, depth=0):
        print '\t' * depth + self._repr_headline()
        for child in sorted(self.children, key=lambda x: x.name):
            child.pprint(depth + 1)
    
    def _process(self, root, processor):
        for child in self.children:
            child._process(root, processor)
    
    def preview(self, root):
        self._process(root, processor.Previewer('$schema', ''))
    
    def create(self, root, verbose=False):
        self._process(root, processor.Processor(verbose=verbose))
    
    def tag_existing(self, root, verbose=False):
        for child in self.children:
            self.tag_existing(root, verbose=verbose)


class Directory(Structure):
    
    def __init__(self, context, config):
        super(Directory, self).__init__(context, config)
        
        template = config.get('template')
        if template:
            self._scan_template(template)
    
    def _process(self, root, processor):
        
        path = os.path.join(root, self.name).rstrip('/')
        
        if not os.path.exists(path):
            processor.mkdir(path)
            
        for child in self.children:
            child._process(path, processor)
        
    def _scan_template(self, template):
        
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
            config.setdefault('type', 'directory')
            
            local_template = os.path.splitext(special)[0]
            if os.path.exists(local_template):
                config['template'] = local_template
                paths.remove(local_template)
                
            child = Structure.from_context(self.context, config)
            if child is not None:
                self.children.append(child)
        
        # Generic files/directories.
        for path in [x for x in paths if not x.endswith('.yml')]:
            self.children.append(Structure.from_context(
                self.context, {
                    'name': os.path.basename(path),
                    'type': 'directory' if os.path.isdir(path) else 'file',
                    'template': path,
            }))
    
    def _repr_headline(self):
        return (self.name or '.') + '/'


class Entity(Directory):
    
    @property
    def entity(self):
        return self.context.entity
    
    def _repr_headline(self):
        return '%s/ <- %s %s' % (self.name or '.', self.entity['type'], self.entity['id'])
    
    def tag_existing(self, root, verbose=False):
        
        path = os.path.join(root, self.name).rstrip('/')
        if not os.path.exists(path):
            return
        
        # Tag it, but only if that directory has not already been tagged
        # with this entity. This should not be nessesary once incremental
        # construction is done.
        if not any(x['entity'] is self.entity for x in self.context.sgfs.get_directory_tags(path)):
            processor.comment('.sgfs: %s <- %s %s' % (path, self.entity['type'], self.entity['id']))
            self.context.sgfs.tag_directory_with_entity(path, self.entity)
        
        for child in self.children:
            child.tag_existing(path)
        
    
    def _process(self, root, processor):
        
        path = self.context.sgfs.path_for_entity(self.entity)
        if path is not None:
            from_cache = True
        else:            
            path = os.path.join(root, self.name).rstrip('/')
            from_cache = False
        
        if not os.path.exists(path):
            processor.mkdir(path)
        
        if not from_cache:
            # Tag it, but only if that directory has not already been tagged
            # with this entity. This should not be nessesary once incremental
            # construction is done.
            if not any(x['entity'] is self.entity for x in self.context.sgfs.get_directory_tags(path)):
                processor.comment('.sgfs: %s <- %s %s' % (path, self.entity['type'], self.entity['id']))
                self.context.sgfs.tag_directory_with_entity(path, self.entity)
        
        for child in self.children:
            child._process(path, processor)
        


class Include(Directory):
    
    def pprint(self, depth):
        for child in self.children:
            child.pprint(depth)


class File(Structure):
    
    def _repr_headline(self):
        return self.name
    
    def _process(self, root, processor):
        path = os.path.join(root, self.name).rstrip('/')
        if not os.path.exists(path):
            template = self.config.get('template')
            if template:
                processor.copy(template, path)
            else:
                processor.touch(path)


