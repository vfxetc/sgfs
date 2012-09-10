import copy

class Context(object):
    
    def __init__(self, entity):
        self.entity = entity
        self.children = []
        self.parent = None
        
    def copy(self):
        return copy.copy(self)
    
    def __repr__(self):
        return '<Context %s:%s at 0x%x>' % (self.entity['type'], self.entity['id'], id(self))
    
    def pprint(self, depth=0):
        print '%s%s:%s' % (
            '\t' * depth,
            self.entity['type'],
            self.entity['id'],
        ),
        if not self.children:
            print
            return
        elif len(self.children) == 1:
            print '->',
            self.children[0].pprint(depth)
            return
        
        print '{'
        for child in self.children:
            child.pprint(depth + 1)
        print '\t' * depth + '}'
    
    @property
    def is_linear(self):
        if not self.children:
            return True
        return len(self.children) == 1 and self.children[0].is_linear

    @property
    def linear_base(self):
        base = [self]
        while len(base[-1].children) == 1:
            base.append(base[-1].children[0])
        return base
    
    def iter_leafs(self):
        if not self.children:
            yield self
        else:
            for child in self.children:
                for leaf in child.iter_leafs():
                    yield leaf
    
    def iter_by_type(self, type_):
        if self.entity['type'] == type_:
            yield self
        for child in self.children:
            for entity in child.iter_by_type(type_):
                yield entity
    
    def iter_linearized(self):
        if not self.children:
            new = self.copy()
            new.parent = None
            yield new
        for child in self.children:
            for child_ctx in child.iter_linearized():
                ctx = self.copy()
                ctx.children = [child_ctx]
                child_ctx.parent = ctx
                yield ctx
    