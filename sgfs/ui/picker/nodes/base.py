import threading
import traceback
import multiprocessing.pool
import Queue as queue

from PyQt4 import QtCore
Qt = QtCore.Qt

from ..childlist import ChildList
from ..utils import debug


class Node(object):

    @staticmethod
    def is_next_node(state):
        raise NotImplementedError()
    
    def __init__(self, model, key, view_data, state):
        
        if not self.is_next_node(state):
            raise TypeError('not next state')
        
        self.model = model
        self.key = key
        
        # These are set by the model.
        self.index = None
        self.parent = None
        self.view = None
        
        self.view_data = {}
        self.state = {}
        self.update(view_data, state)
        
        self._child_lock = threading.RLock()
        self._flat_children = None
        self._children = None
        self.error_count = 0
        self.is_loading = 0
    
    def reset(self):
        signal = self.index and self.children()
        if signal:
            self.model.beginRemoveRows(self.index, 0, len(self.children()))
        self._flat_children = None
        self._children = None
        self.error_count = 0
        self.is_loading = 0
        self.children()
        if signal:
            self.model.endRemoveRows()
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def update(self, view_data, state):
        is_different = any(self.view_data.get(k) != v for k, v in view_data.iteritems())
        self.view_data.update(view_data)
        self.state.update(state)
        if is_different and self.index:
            self.model.dataChanged.emit(self.index, self.index)
    
    def is_leaf(self):
        return False
    
    def add_child_menu_actions(self, child, menu):
        pass
    
    def child_matches_initial_state(self, child, init_state):
        try:
            return all(init_state[k] == v for k, v in child.state.iteritems())
        except KeyError:
            pass
    
    def fetch_children(self):
        if hasattr(self, 'fetch_async_children'):
            self.schedule_async_fetch(self.fetch_async_children)
        return []
        
    def schedule_async_fetch(self, callback, *args, **kwargs):
        self.is_loading += 1
        self.model.threadpool.submit(self._process_async, callback, *args, **kwargs)
        
    def _process_async(self, callback, *args, **kwargs):
        try:
            
            # Since callback may be a generator, for it to completion before we
            # grab the update lock.
            children = list(callback(*args, **kwargs))
        
        except Exception as e:
            self.error_count += 1
            self.is_loading -= 1
            self.model.dataChanged.emit(self.index, self.index)
            raise
            
        try:

            # This forces the update to wait until after the first (static)
            # children have been put into place, even if this function runs
            # very quickly.
            with self._child_lock:
                self.is_loading -= 1
                self.add_raw_children(children)
        
        except Exception as e:
            self.model.dataChanged.emit(self.index, self.index)
            raise
        
        
    def get_temp_children_from_state(self, init_state):
        """Return temporary children that we can from the given init_state, so
        that there is something there while we load the real children."""
        return []
    
    def groups_for_child(self, node):
        """Return raw tuples for all of the groups that the given node should
        lie under.
        
        Defaults to asking the node itself for the groups."""
        return node.groups()
    
    def groups(self):
        """See groups_for_child. Defaults to pulling groups out of view_data."""
        return self.view_data.get('groups') or []
    
    def add_raw_children(self, raw_children):
        with self._child_lock:
            self._add_raw_children(raw_children)
    
    def _add_raw_children(self, raw_children):

        signal = self.index is not None and self._children is not None
        if signal:
            self.model.layoutAboutToBeChanged.emit()
        
        # Initialize the child list if we haven't already.
        self._flat_children = flat_children = self._flat_children or ChildList()
        
        # Create the children in a flat list.
        for key, view_data, new_state in raw_children:
            
            full_state = dict(self.state)
            full_state.update(new_state)
            
            # Update old nodes if we have them, otherwise create a new one.
            node = flat_children.pop(key, None)
            if node is not None:
                node.update(view_data, full_state)
            else:
                node = self.model.construct_node(key, view_data, full_state)
            
            flat_children.append(node)
        
        # This will hold the heirarchical children.
        self._children = self._children or ChildList()
        
        for node in flat_children:
            
            groups = list(self.groups_for_child(node))
            
            # Find the parent for the new node. If there are no groups, then it
            # will be self.
            parent = self
            for key, view_data, new_state in groups:
                
                # Create the new group if it doesn't already exist.
                group = parent.children().pop(key, None)
                if group is None:
                    node.state.update(new_state)
                    group_state = dict(parent.state)
                    group_state.update(new_state)
                    group = Group(self.model, key, view_data, group_state)
                parent.children().append(group)
                
                # Look here next.
                parent = group
            
            # Attach the node to its parent at the end of the list.
            parent.children().pop(node.key, None)
            parent.children().append(node)
        
        # Rebuild all indexes and lineage.
        self._repair_heirarchy()
        
        if signal:
            self.model.layoutChanged.emit()
            if self.view:
                try:
                    self.view.layoutChanged.emit()
                
                # Silence a threading error.
                except TypeError:
                    pass
    
    def _repair_heirarchy(self):
        changes = list(self._repair_heirarchy_recurse())
        if changes:
            self.model.changePersistentIndexList(
                [x[0] for x in changes],
                [x[1] for x in changes],
            )
    
    def sort_children(self):
        self.children().sort(key=lambda n: n.view_data[Qt.DisplayRole])
    
    def _repair_heirarchy_recurse(self):
        self.sort_children()
        for i, child in enumerate(self.children()):
            if not child.index or (child.index and child.index.row() != i):
                new = self.model.createIndex(i, 0, child)
                if child.index:
                    yield child.index, new
                child.index = new
            child.parent = self
            if isinstance(child, Group):
                for x in child._repair_heirarchy_recurse():
                    yield x
    
    def children(self):
        with self._child_lock:
            if self._children is None:
                initial_children = list(self.fetch_children() or ())
                self.add_raw_children(initial_children)
            return self._children


class Group(Node):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def child_matches_initial_state(self, child, init_state):
        # Dispatch to the first real parent.
        return self.parent.child_matches_initial_state(child, init_state)
    
    def add_child_menu_actions(self, child, menu):
        self.parent.add_child_menu_actions(child, menu)
        
    def fetch_children(self):
        return []
    
    def reset(self):
        self.parent.reset()


class Leaf(Node):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def is_leaf(self):
        return True
    
    def fetch_children(self):
        return []