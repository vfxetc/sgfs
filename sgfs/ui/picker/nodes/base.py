import threading

import concurrent.futures

from ..childlist import ChildList

threadpool = concurrent.futures.ThreadPoolExecutor(1)


class Node(object):

    @staticmethod
    def is_next_node(state):
        raise NotImplementedError()
    
    def __init__(self, model, key, view_data, state):
        
        if not self.is_next_node(state):
            raise TypeError('not next state')
        
        self.model = model
        self.key = key
        
        self.view_data = None
        self.state = None
        self.update(view_data or {}, state or {})
        
        # These are set by the model.
        self.index = None
        self.parent = None
        
        self._child_lock = threading.RLock()
        self._created_children = None
        self._direct_children = None
        self.is_loading = 0
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def update(self, view_data, state):
        self.view_data = view_data
        self.state = state
    
    def is_leaf(self):
        return False
    
    def child_matches_init_state(self, state, init_state):
        try:
            return all(init_state[k] == v for k, v in state.iteritems())
        except KeyError:
            pass
    
    def fetch_children(self, init_state):
        
        # debug('fetch_children')
        
        if hasattr(self, 'fetch_async_children'):
            self.schedule_async_fetch(self.fetch_async_children)
        
        # Return any children we can figure out from the init_state.
        if init_state is not None:
            return self.get_initial_children(init_state) or []
        
        return []
        
    def schedule_async_fetch(self, callback, *args, **kwargs):
        self.is_loading += 1
        threadpool.submit(self._process_async, callback, *args, **kwargs)
        
    def _process_async(self, callback, *args, **kwargs):
        try:
            
            # Since callback may be a generator, for it to completion before we
            # grab the update lock.
            children = list(callback(*args, **kwargs))
        
            # debug('2nd fetch_children (async) is done')
        
            # This forces the update to wait until after the first (static) children
            # have been put into place, even if this function runs very quickly.
            with self._child_lock:
                # debug('2nd replace_children (async)')
                self.is_loading -= 1
                self._update_children(children)
        
        except Exception as e:
            traceback.print_exc()
            raise
        
    def get_initial_children(self, init_state):
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
    
    def _update_children(self, updated):
        
        signal = self.index is not None and self._direct_children is not None
        if signal:
            # debug('    layoutAboutToBeChanged')
            self.model.layoutAboutToBeChanged.emit()
        
        # Initialize the child list if we haven't already.
        self._created_children = flat_children = self._created_children or ChildList()
        
        # Create the children in a flat list.
        for key, view_data, new_state in updated:
            
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
        self._direct_children = self._direct_children or ChildList()
        
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
                    state = dict(parent.state)
                    state.update(new_state)
                    group = Group(self.model, key, view_data, state)
                parent.children().append(group)
                
                # Look here next.
                parent = group
            
            # Attach the node to its parent at the end of the list.
            parent.children().pop(node.key, None)
            parent.children().append(node)
        
        # Rebuild all indexes and lineage.
        self._repair_heirarchy()
        
        if signal:
            # debug('    layoutChanged')
            self.model.layoutChanged.emit()
    
    def _repair_heirarchy(self):
        changes = list(self._repair_heirarchy_recurse())
        if changes:
            self.model.changePersistentIndexList(
                [x[0] for x in changes],
                [x[1] for x in changes],
            )
            
    def _repair_heirarchy_recurse(self):
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
    
    def children(self, init_state=None):
        with self._child_lock:
            if self._direct_children is None:
                # debug('1st fetch_children')
                initial_children = list(self.fetch_children(init_state))
                # debug('1st replace_children')
                self._update_children(initial_children)
            return self._direct_children


class Group(Node):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def child_matches_init_state(self, state, init_state):
        return self.parent.child_matches_init_state(state, init_state)
    
    def __init__(self, model, key, view_data, state):
        super(Group, self).__init__(model, key, view_data, state)
        self._children = ChildList()
    
    def children(self, *args):
        # debug('Group children: %r', self._children)
        return self._children


class Leaf(Node):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def is_leaf(self):
        return True
    
    def fetch_children(self, init_state):
        return []