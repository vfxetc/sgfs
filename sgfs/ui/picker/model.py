import sys
import os
import threading
import traceback

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

from .nodes.base import Node, Group, Leaf
from .utils import debug


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    _pixmaps = {}
    
    def __init__(self, root_state=None, sgfs=None, shotgun=None, session=None):
        super(Model, self).__init__()
        
        self._root_state = root_state or {}
        self._root = None
        
        self.sgfs = sgfs or SGFS(shotgun=shotgun, session=session)
        
        self._node_types = []
    
    def register_node_type(self, node_type):
        self._node_types.append(node_type)
    
    def index_from_state(self, state):
        
        # debug('set_initial_state')
        
        last_match = None
        nodes = [self.root()]
        while True:
            
            if not nodes:
                break
            
            node = nodes.pop(0)
            
            # Skip the root.
            if node.parent is None:
                nodes.extend(node.children())
                continue
            
            # Skip over groups. It would be nice if the group class would be
            # able to property handle this logic, but we don't want a "positive
            # match" (for the purposes of traversing the group) to result in
            # not selecting something real (because it is at a lower level than
            # the last group).
            if isinstance(node, Group):
                # debug('skipping group')
                nodes.extend(node.children())
                continue
            
            # debug('matches via %r:\n\t\t\t\t%r', node.parent, sorted(node.state))
            if node.parent.child_matches_initial_state(node, state):
                # debug('!! YES !!')
                
                # Trigger initial async.
                node.children()
                
                node._update_children(node.get_children_from_state(state))
                nodes.extend(node.children())
                last_match = node
        
        if last_match:
            # debug('last_match: %r', last_match)
            # debug('last_match.index: %r', last_match.index)
            # debug('last_match.state: %r', last_match.state)
            return last_match.index
        else:
            pass# debug('Did not find a match.')
    
    def construct_node(self, key, view_data, state):
        for node_type in self._node_types:
            try:
                return node_type(self, key, view_data, state)
            except TypeError:
                pass
        return Leaf(self, key, view_data, state)
        
    def hasChildren(self, index):
        node = self.node_from_index(index)
        res = not node.is_leaf()
        # debug('%r.hasChildren: %r', node, res)
        return res
    
    def root(self):
        if self._root is None:
            self._root = self.construct_node(None, {}, self._root_state)
            self._root.index = QtCore.QModelIndex()
            self._root.parent = None
        return self._root
    
    def node_from_index(self, index):
        return index.internalPointer() if index.isValid() else self.root()
    
    def headerData(self, section, orientation, role):
        
        if role == Qt.DisplayRole:
            # This is set by the HeaderedListView widgets as they are being painted.
            # I.e.: This is a huge hack.
            return self._header
        
        return QtCore.QVariant()
    
    def rowCount(self, parent):
        node = self.node_from_index(parent)
        res = len(node.children())
        # debug('%r.rowCount: %d', node, res)
        return res
    
    def columnCount(self, parent):
        return 1
    
    def index(self, row, col, parent):
        
        if col > 0:
            return QtCore.QModelIndex()
        
        node = self.node_from_index(parent)
        try:
            child = node.children()[row]
        except IndexError:
            return QtCore.QModelIndex()
        
        if child.index is None:
            debug('child.index is None: %r', child)
            child.index = self.createIndex(row, col, child)
            if child.parent is None:
                debug('\tchild.parent is also None')
                child.parent = node
        
        # debug('index %d of %r -> %r', row, node, child)
        return child.index
    
    def parent(self, child):
        node = self.node_from_index(child)
        if node.parent is not None:
            return node.parent.index
        else:
            return QtCore.QModelIndex()
    
    def data(self, index, role):
        
        if not index.isValid():
            return QtCore.QVariant()

        node = self.node_from_index(index)
        
        if role == Qt.DisplayRole:
            data = node.view_data.get(Qt.DisplayRole, repr(node))
            # debug('displayRole for %r -> %r', node, data)
            return data
        
        if role == Qt.DecorationRole:
            
            node = self.node_from_index(index)
            data = node.view_data.get(Qt.DecorationRole)
            
            if data is None:
                return QtCore.QVariant()
            
            if isinstance(data, QtGui.QColor):
                key = (data.red(), data.green(), data.blue())
                if key not in self._pixmaps:
                    pixmap = QtGui.QPixmap(16, 16)
                    painter = QtGui.QPainter(pixmap)
                    painter.eraseRect(0, 0, 16, 16)
                    brush = QtGui.QBrush(data)
                    painter.setBrush(brush)
                    painter.setPen(data.darker())
                    painter.drawRect(2, 2, 12, 12)
                    painter.end()
                    self._pixmaps[key] = pixmap
                return self._pixmaps[key]
            
            if isinstance(data, basestring):
                if data not in self._pixmaps:
                    self._pixmaps[data] = QtGui.QPixmap(data)
                return self._pixmaps[data]
            
            return data
        
        # Passthrough other roles.
        try:
            return node.view_data[role]
        except KeyError:
            return QtCore.QVariant()









        

    
