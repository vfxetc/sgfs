import fnmatch
import os
import subprocess

import yaml

from .processor import Processor
from . import utils


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
    
    def create(self, root, verbose=False, dry_run=False):
        processor = Processor(verbose=verbose, dry_run=dry_run)
        self._create(root, processor)
        return processor.log_events
        
    def _create(self, root, processor):
        for child in self.children:
            child._create(root, processor)
    
    def tag_existing(self, root, verbose=False, dry_run=False):
        for child in self.children:
            for x in child.tag_existing(root, verbose=verbose, dry_run=dry_run):
                yield x


class Directory(Structure):
    
    def __init__(self, context, config):
        super(Directory, self).__init__(context, config)
        
        template = config.get('template')
        if template:
            self._scan_template(template)
    
    def _create(self, root, processor):
        
        path = os.path.join(root, self.name).rstrip('/')
        
        if not os.path.exists(path):
            processor.mkdir(path)
            
        for child in self.children:
            child._create(path, processor)
        
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
    
    def tag_existing(self, root, verbose=False, dry_run=False):
        
        path = os.path.join(root, self.name).rstrip('/')
        if not os.path.exists(path):
            return
        
        # Tag it if it wasn't already.
        if not any(tag['entity'] is self.entity for tag in self.context.sgfs.get_directory_entity_tags(path)):
            yield self.entity, path
            if verbose:
                print '# tag %r with %s %d' % (path, self.entity['type'], self.entity['id'])
            if not dry_run:
                self.context.sgfs.tag_directory_with_entity(path, self.entity)
            
        for child in self.children:
            for x in child.tag_existing(path, verbose=verbose, dry_run=dry_run):
                yield x
    
    def _create(self, root, processor):
        
        path = self.context.sgfs.path_for_entity(self.entity)
        from_cache = path is not None
        path = path if from_cache else os.path.join(root, self.name).rstrip('/')
        
        if not os.path.exists(path):
            processor.mkdir(path)
        
        if not from_cache and not processor.dry_run:
            self.context.sgfs.tag_directory_with_entity(path, self.entity)
        
        for child in self.children:
            child._create(path, processor)
        


class Include(Directory):
    
    def pprint(self, depth):
        for child in self.children:
            child.pprint(depth)


class File(Structure):
    
    def _repr_headline(self):
        return self.name
    
    def _create(self, root, processor):
        path = os.path.join(root, self.name).rstrip('/')
        if not os.path.exists(path):
            template = self.config.get('template')
            if template:
                processor.copy(template, path)
            else:
                processor.touch(path)


