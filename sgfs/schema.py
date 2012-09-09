import os

import yaml


class Schema(object):
    
    def __init__(self, root, entity_type, spec=None):
        
        self.root = root
        self.entity_type = entity_type
        self.spec = spec if spec is not None else {}
        
        path = os.path.join(root, entity_type + '.yml')
        self.config = yaml.load(open(path).read())
        
        self.children = {}
        for type_, spec in self.config.get('children', {}).iteritems():
            self.children[type_] = Schema(root, type_, spec)
    
    def __repr__(self):
        return '<Schema %s:%s at 0x%x>' % (os.path.basename(self.root), self.entity_type, id(self))
    
    @property
    def template(self):
    
        try:
            return self.config['template']
        except KeyError:
            pass
            
        path = os.path.join(root, path)
        if os.path.exists(default_template_path):
            return path
        
        return None

