import fnmatch
import os

import yaml

from .processor import Processor
from . import utils
from .template import BoundTemplate



class Structure(object):
    
    @classmethod
    def from_context(cls, context, config, root):
        
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
            filename='sgfs.schema.%s.%s' % (context.entity['type'], 'condition')
        ):
            return constructor(context, config, root)

    
    def __init__(self, context, config, root):
        
        self.context = context
        self.config = config
        
        # Delegate to subclasses.
        self._set_name_and_path(root)
        
        self.children = []
    
    def _set_name_and_path(self, root):
        self.name = str(self.get_or_eval('name', ''))
        if self.name:
            self.path = os.path.join(root, self.name)
        else:
            self.path = root
    
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
                filename='sgfs.schema.%s.%s' % (self.context.entity['type'], name)
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
    
    def walk(self, depth_first=False):
        """Walk depth-first, yielding ``(path, node)`` pairs."""
        if not depth_first:
            yield self
        for child in self.children:
            for x in child.walk(depth_first):
                yield x
        if depth_first:
            yield self
    
    def create(self, **kwargs):
        processor = Processor(**kwargs)
        for node in self.walk():
            node._create(processor)
        return processor.log_events
        
    def _create(self, processor):
        pass
    
    def tag_existing(self, **kwargs):
        res = []
        processor = Processor(**kwargs)
        for node in self.walk():
            x = node._tag_existing(processor)
            if x:
                res.append(x)
        return res
    
    def _tag_existing(self, processor):
        pass
    
    def iter_templates(self, name):
        for node in self.walk(depth_first=True):
            for name_pattern, raw_template in node.config.get('templates', {}).iteritems():
                if fnmatch.fnmatchcase(name, name_pattern):
                    yield BoundTemplate(raw_template, structure=node)
            


class Directory(Structure):
    
    def __init__(self, context, config, root):
        super(Directory, self).__init__(context, config, root)
        template = config.get('template')
        if template:
            self._scan_template(template)
    
    def _create(self, processor):
        if not os.path.exists(self.path):
            processor.mkdir(self.path)
        
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
                
            child = Structure.from_context(self.context, config, self.path)
            if child is not None:
                self.children.append(child)
        
        # Generic files/directories.
        for path in [x for x in paths if not x.endswith('.yml')]:
            self.children.append(Structure.from_context(
                self.context, {
                    'name': os.path.basename(path),
                    'type': 'directory' if os.path.isdir(path) else 'file',
                    'template': path,
                }, self.path,
            ))
    
    def _repr_headline(self):
        return (self.name or '.') + '/'


class Entity(Directory):
    
    def _set_name_and_path(self, root):
        self.existing_path = self.sgfs.path_for_entity(self.entity)
        if self.existing_path:
            self.path = self.existing_path
            self.name = os.path.basename(self.path)
        else:
            super(Entity, self)._set_name_and_path(root)
        
    @property
    def entity(self):
        return self.context.entity
    
    def _repr_headline(self):
        return '%s/ <- %s %s' % (self.name or '.', self.entity['type'], self.entity['id'])
    
    def _tag_existing(self, processor):
        
        if not os.path.exists(self.path):
            return
        
        # Skip this one if it has already been done.
        if any(tag['entity'] is self.entity for tag in self.sgfs.get_directory_entity_tags(self.path)):
            return
        
        processor.comment('tag %r with %s %d' % (self.path, self.entity['type'], self.entity['id']))
        if not processor.dry_run:
            self.sgfs.tag_directory_with_entity(self.path, self.entity)
            
        return self.entity, self.path

    def _create(self, processor):
        
        # If this is from the cache, then clearly we don't need to tag it.
        # If this is a dry run, we also don't care about asserting permissions.
        if not self.existing_path and not processor.dry_run:
            
            # Don't let people create Projects.
            processor.assert_allow_entity(self.entity)
            
            if not os.path.exists(self.path):
                processor.mkdir(self.path)
            self.sgfs.tag_directory_with_entity(self.path, self.entity)
        


class Include(Directory):
    
    def _set_name_and_path(self, root):
        self.path = root
        self.name = ''
    
    def pprint(self, depth):
        for child in self.children:
            child.pprint(depth)


class File(Structure):
    
    def _repr_headline(self):
        return self.name
    
    def _create(self, processor):
        if not os.path.exists(self.path):
            template = self.config.get('template')
            if template:
                processor.copy(template, self.path)
            else:
                processor.touch(self.path)

