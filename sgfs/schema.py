import os

import yaml

from . import structure
from . import utils




class Schema(object):
    
    def __init__(self, root, entity_type, config=None):
        
        self.root = root
        self.entity_type = entity_type
        
        # Load the child config over top of the one provided by the parent.
        self.config = dict(config or {})
        config_path = os.path.join(root, self.config.get('config', entity_type + '.yml'))
        if os.path.exists(config_path):
            self.config.update(yaml.load(open(config_path).read()))
            self.config['__file__'] = config_path
        elif 'config' in self.config:
            raise ValueError('%r does not exist' % self.config['config'])
        else:
            self.config['__file__'] = None
        
        # Load all the children.
        self.children = {}
        for type_, child_config in self.config.get('children', {}).iteritems():
            self.children[type_] = Schema(root, type_, child_config)
    
    def __repr__(self):
        return '<Schema %s:%s at 0x%x>' % (os.path.basename(self.root), self.entity_type, id(self))
    
    def pprint(self, depth=0):
        print '%s%s at 0x%x' % (
            '\t' * depth,
            self.entity_type,
            id(self)
        ),
        if not self.children:
            print
            return
        
        print '{'
        for type_, child in sorted(self.children.iteritems()):
            child.pprint(depth + 1)
        print '\t' * depth + '}'
    
    @property
    def template(self):
    
        try:
            return self.config['template']
        except KeyError:
            pass
            
        path = os.path.join(self.root, self.entity_type)
        if os.path.exists(path):
            return path
        
        return None
    
    def structure(self, context):
        return self._structure(context, globals_={})
    
    def _structure(self, context, globals_):
        
        print 'STRUCTURE', context
        
        if self.entity_type != context.entity['type']:
            raise ValueError('context entity type does not match; %r != %r' % (
                self.entity_type, context.entity['type']
            ))
        
        globals_[self.entity_type.lower()] = context.entity
        globals_['self'] = context.entity
        locals_ = self.config.copy()
        
        children = []
        for child in context.children:
            child_type = child.entity['type']
            if child_type in self.children:
                children.append(self.children[child_type]._structure(child, globals_.copy()))
        
        template = self.template
        if template:
            return structure.Entity(globals_, locals_, children, template=template)
        else:
            return structure.Entity(globals_, locals_, children)
        
    

