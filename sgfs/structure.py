import fnmatch
import os
import subprocess

import yaml

from .processor import Processor
from . import utils
from template import Template



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
            raise ValueError('invalid structure type; %r' % type_)
        
        # Make sure there isn't a condition, or that it is satisfied.
        condition = config.get('condition')
        if not condition or utils.eval_expr_or_func(
            condition,
            context.build_eval_namespace(config),
        ):
            return constructor(context, config)

    
    def __init__(self, context, config):
        
        self.context = context
        self.config = config
        
        self.name = str(self.get_or_eval('name', ''))
        self.children = []
    
    @property
    def sgfs(self):
        return self.context.sgfs
    
    def get_or_eval(self, name, default=None):
        if name in self.config:
            return self.config[name]
        expr_name = name + '_expr'
        if expr_name in self.config:
            return utils.eval_expr_or_func(
                self.config[expr_name],
                self.context.build_eval_namespace(self.config),
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
    
    def walk(self, path='', children_first=False):
        """Walk depth-first, yielding ``(path, node)`` pairs."""
        if self.name:
            path = os.path.join(path, self.name)
        if not children_first:
            yield path, self
        for child in self.children:
            for x in child.walk(path):
                yield x
        if children_first:
            yield path, self
    
    def create(self, root, **kwargs):
        processor = Processor(**kwargs)
        self._create(root, processor)
        return processor.log_events
        
    def _create(self, root, processor):
        for child in self.children:
            child._create(root, processor)
    
    def tag_existing(self, root, **kwargs):
        res = []
        processor = Processor(**kwargs)
        for path, node in self.walk(root):
            x = node._tag_existing(path, processor)
            if x:
                res.append(x)
        return res
    
    def _tag_existing(self, path, processor):
        pass
    
    def iter_templates(self, name):
        for path, node in self.walk(children_first=True):
            template_string = node.config.get('templates', {}).get(name)
            if template_string is not None:
                yield Template(template_string, path=path, namespace=_namespace_from_context(self.context, self.config))
            


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
            config.setdefault('name', os.path.basename(os.path.splitext(special)[0]))
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
    
    def _tag_existing(self, path, processor):
        
        if not os.path.exists(path):
            return
        
        # Skip this one if it has already been done.
        if any(tag['entity'] is self.entity for tag in self.sgfs.get_directory_entity_tags(path)):
            return
        
        processor.comment('tag %r with %s %d' % (path, self.entity['type'], self.entity['id']))
        if not processor.dry_run:
            self.sgfs.tag_directory_with_entity(path, self.entity)
            
        return self.entity, path

    def _create(self, root, processor):
        
        # Latch onto existing paths instead of what the structure says we should
        # create, to allow for users to mutate the structure after it has been
        # partially created.
        existing_path = self.sgfs.path_for_entity(self.entity)
        path = existing_path or os.path.join(root, self.name).rstrip('/')
        
        # If this is from the cache, then clearly we don't need to tag it.
        # If this is a dry run, we also don't care about asserting permissions.
        if not existing_path and not processor.dry_run:
            
            # Don't let people create Projects.
            processor.assert_allow_entity(self.entity)
            
            if not os.path.exists(path):
                processor.mkdir(path)
            self.sgfs.tag_directory_with_entity(path, self.entity)
        
        for child in self.children:
            child._create(path, processor)
        


class Include(Directory):
    
    def __init__(self, *args, **kwargs):
        super(Include, self).__init__(*args, **kwargs)
        self.name = ''
    
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


