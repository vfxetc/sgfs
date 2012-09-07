

class Context(object):
    
    def __init__(self, entity):
        self.entity = entity
        self.parent = None
        self.children = []
    
    def __repr__(self):
        return '<Context %s:%s at 0x%x>' % (self.entity['type'], self.entity['id'], id(self))
    
    def pprint(self, depth=0):
        print '%s- %s:%s at 0x%x' % ('\t' * depth, self.entity['type'], self.entity['id'], id(self))
        for child in self.children:
            child.pprint(depth + 1)
