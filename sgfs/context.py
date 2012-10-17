import copy

class Context(object):
    
    """A selection of Shotgun entities and their relationship.
    
    A Context is a directed acyclic graph of Shotgun entities. It is usually
    rooted at a ``Project``, but technically there is no such restriction. This
    class exists solely to encapsulate a selection of entities and to be able
    to navigate and query their graph.
    
    """
    
    def __init__(self, sgfs, entity):
        self.sgfs = sgfs
        self.entity = entity
        self.children = []
        self.parent = None
        
    def copy(self):
        return copy.copy(self)
    
    def __repr__(self):
        return '<Context %s:%s at 0x%x>' % (self.entity['type'], self.entity['id'], id(self))
    
    def project(self):
        """Retrieve the root ``Project`` node which owns this node."""
        ctx = self
        while ctx.parent:
            ctx = ctx.parent
        if ctx.entity['type'] == 'Project':
            return ctx
    
    def pprint(self, depth=0):
        """Pretty-print the graph."""
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
    def _dotname(self):
        return '%s_ctx_%x' % (self.entity['type'].lower(), id(self))
    
    def dot(self):
        return ''.join(self._dot())
    
    def _dot(self):
        """Construct a GraphViz dot graph of this node and its children."""
        name_field = {
            'Project': 'name',
            'Sequence': 'code',
            'Shot': 'code',
            'Task': 'content',
        }.get(self.entity['type'])
        name = name_field and self.entity.get(name_field)
        label_parts = ['%s %s' % (self.entity['type'], self.entity['id'])]
        if name:
            label_parts.append('"<B>%s</B>"' % name)
        yield '%s [label=<%s>]\n' % (self._dotname, '<BR/>'.join(label_parts))
        for i, child in enumerate(self.children):
            yield '%s -> %s [label="%d"]\n' % (self._dotname, child._dotname, i)
            yield child.dot()
    
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
    