from __future__ import absolute_import

import copy

from sgfs import utils


class Context(object):
    
    """A selection of Shotgun entities and their relationship.
    
    A :class:`Context` is a directed acyclic graph of Shotgun entities. It is usually
    rooted at a ``Project``, but technically there is no such restriction. This
    class exists solely to encapsulate a selection of entities and to be able
    to navigate and query their graph.
    
    Each node in a context graph is an instance of this class, and its children
    are stored in the ``children`` list. :class:`Context` graphs should be
    constructed by a :class:`.SGFS` object.
    
    """
    
    def __init__(self, sgfs, entity):
        
        #: The :class:`~sgfs.sgfs.SGFS` object this context was created by.
        self.sgfs = sgfs
        
        #: The entity this node represents.
        self.entity = entity
        
        #: A list of ``Context`` nodes.
        self.children = []
        
        #: This node's parent; sometimes ``None``.
        self.parent = None
        
    def copy(self):
        """Shallow copy the :class:`Context`; children and entities remain references."""
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
    
    def pprint(self):
        """Pretty-print the graph."""
        self._pprint(0)
    
    def _pprint(self, depth):
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
            self.children[0]._pprint(depth)
            return
        
        print '{'
        for child in self.children:
            child._pprint(depth + 1)
        print '\t' * depth + '}'
    
    @property
    def _dotname(self):
        return '%s_ctx_%x' % (self.entity['type'].lower(), id(self))
    
    def dot(self):
        """Get a GraphViz ``dot`` graph representing the context."""
        return ''.join(self._dot())
    
    def _dot(self):
        """Construct a GraphViz ``dot`` graph of this node and its children."""
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
        """Is the entire graph linear? E.g. Do all nodes have only a single child?"""
        if not self.children:
            return True
        return len(self.children) == 1 and self.children[0].is_linear

    @property
    def linear_base(self):
        """The part of the context from the current node that has no forks."""
        base = [self]
        while len(base[-1].children) == 1:
            base.append(base[-1].children[0])
        return base
    
    def iter_leafs(self):
        """An iterator yielding the leafs of the context graph (e.g. those
        which have no children.)"""
        if not self.children:
            yield self
        else:
            for child in self.children:
                for leaf in child.iter_leafs():
                    yield leaf
    
    def iter_by_type(self, type_):
        """An iterator yielding all nodes in the context graph of the given type.
        
        :param str type_: The Shotgun entity type; e.g. ``"Shot"``.
        
        """
        if self.entity['type'] == type_:
            yield self
        for child in self.children:
            for entity in child.iter_by_type(type_):
                yield entity
    
    def iter_linearized(self):
        """An iterator yielding all possible linear paths from the given root
        through to all of the leafs."""
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
    
    def build_eval_namespace(self, base=None):
        namespace = dict(base or {})
        namespace['self'] = self.entity
        head = self
        while head:
            namespace[head.entity['type']] = head.entity
            head = head.parent
        return namespace
    