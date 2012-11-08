# import gevent.monkey
# gevent.monkey.patch_socket()

import sys
import os
import random
import threading
import collections
import functools
import time
import thread
import traceback
import pprint

import concurrent.futures

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

sgfs = SGFS()


threadpool = concurrent.futures.ThreadPoolExecutor(1)


# sys.path.append('/home/mboers/Documents/RemoteConsole')
# import remoteconsole 
# remoteconsole.spawn(('', 12345), globals())

_debug_start = time.time()
_debug_last = _debug_start
_debug_thread_ids = {}
def debug(msg, *args):
    global _debug_last
    if args:
        msg = msg % args
    ident = _debug_thread_ids.setdefault(thread.get_ident(), len(_debug_thread_ids))
    current_time = time.time()
    sys.stdout.write('%8.3f (%8.3f) %3d %s\n' % ((current_time - _debug_start) * 1000, (current_time - _debug_last) * 1000, ident, msg))
    sys.stdout.flush()
    _debug_last = current_time


class ChildList(list):
    
    def pop(self, key, *args):
        
        if isinstance(key, int):
            return super(ChildList, self).pop(key, *args)
        
        for i, child in enumerate(self):
            if child.key == key:
                break
        else:
            if args:
                return args[0]
            else:
                raise KeyError(key)
        return self.pop(i)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default
        
    def __getitem__(self, key):
        if not isinstance(key, int):
            for child in self:
                if child.key == key:
                    return child
            raise KeyError(key)
        return super(ChildList, self).__getitem__(key)


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
    
    def matches_init_state(self, init_state):
        try:
            return all(init_state[k] == v for k, v in self.state.iteritems())
        except KeyError:
            pass
    
    def fetch_children(self, init_state):
        
        # debug('fetch_children')
        
        if hasattr(self, 'fetch_async_children'):
            self.schedule_async_fetch(self.fetch_async_children)
        
        # Return any children we can figure out from the init_state.
        if init_state is not None and self.matches_init_state(init_state):
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
        old = []
        new = []
        for o, n in self._repair_heirarchy_recurse():
            old.append(o)
            new.append(n)
        if old:
            self.model.changePersistentIndexList(old, new)
            
    def _repair_heirarchy_recurse(self):
        for i, child in enumerate(self.children()):
            if not child.index or (child.index and child.index.row() != i):
                new = self.model.createIndex(i, 0, child)
                if child.index:
                    yield child.index, new
                child.index = new
            child.parent = self
            child._repair_heirarchy_recurse()
            
        
    
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
    
    def matches_init_state(self, init_state):
        return True
    
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

    
class SGFSRoots(Node):
    
    def update(self, *args):
        super(SGFSRoots, self).update(*args)
        self.view_data.setdefault('header', 'SGFS Project')
        
    @staticmethod
    def is_next_node(state):
        return 'Project' not in state
    
    def fetch_children(self, init_state):
        for project, path in sorted(sgfs.project_roots.iteritems(), key=lambda x: x[0]['name']):
            yield (
                project.cache_key,
                {
                    Qt.DisplayRole: project['name'],
                    Qt.DecorationRole: '/home/mboers/Documents/icons/fatcow/16x16/newspaper.png',
                }, {
                    'Project': project,
                },
            )
            
    
    
class ShotgunQuery(Node):
    
    backrefs = {
        'Project': [None],
        'HumanUser': [None],
        'Asset': [('Project', 'project')],
        'Sequence': [('Project', 'project')],
        'Shot': [('Sequence', 'sg_sequence')],
        'Task': [('Shot', 'entity'), ('Asset', 'entity')],
        'PublishEvent': [('Task', 'sg_link')],
        'Tool': [('Project', 'project')],
        'Ticket': [('Tool', 'sg_tool')],
    }
    
    formats = {
        'Project': ['{Project[name]}'],
        'HumanUser': ['{HumanUser[email]}'],
        'Sequence': ['{Sequence[code]}'],
        'Asset': ['{Asset[sg_asset_type]}', '{Asset[code]}'],
        'Shot': ['{Shot[code]}'],
        'Task': ['{Task[step][code]}', '{Task[content]}'],
        'PublishEvent': ['{PublishEvent[sg_type]}', '{PublishEvent[code]}', 'v{PublishEvent[sg_version]:04d}'],
        'Tool': ['{Tool[code]}'],
        'Ticket': ['{Ticket[title]}'],
    }
    
    icons = {
        'Sequence': '/home/mboers/Documents/icons/fatcow/16x16/film_link.png',
        'Shot': '/home/mboers/Documents/icons/fatcow/16x16/film.png',
        'Task': '/home/mboers/Documents/icons/fatcow/16x16/to_do_list.png',
        'PublishEvent': '/home/mboers/Documents/icons/fatcow/16x16/brick.png',
        'Asset': '/home/mboers/Documents/icons/fatcow/16x16/box_closed.png',
    }
    
    fields = {
        'Task': ['step.Step.color'],
        'Tool': ['code'],
        'Ticket': ['title'],
        'HumanUser': ['firstname', 'lastname', 'email'],
    }
    
    @classmethod
    def specialize(cls, entity_types, **kwargs):
        return functools.partial(cls,
            entity_types=entity_types,
            **kwargs
        )
    
    def __init__(self, *args, **kwargs):
        self.entity_types = kwargs.pop('entity_types')
        super(ShotgunQuery, self).__init__(*args, **kwargs)
    
    def __repr__(self):
        return '<%s for %r at 0x%x>' % (self.__class__.__name__, self.entity_types, id(self))
    
    def is_next_node(self, state):
        # If any types have a backref that isn't satisfied.
        self.active_types = []
        for type_ in self.entity_types:
            if type_ in state or state.get('ignore_%s' % type_):
                continue
            for backref in self.backrefs[type_]:
                if backref is None or backref[0] in state:
                    self.active_types.append(type_)
                    continue
        # debug('is_next_node: %r -> %r', sorted(state.iterkeys()), self.active_types)
        return bool(self.active_types)
    
    def matches_init_state(self, init_state):
        for type_ in self.active_types:
            a = init_state.get(type_)
            b = self.state.get(type_)
            debug('xxx %r %r %r', type_, a, b)
            if a and b and a == b:
                return True
    
    def update(self, *args):
        super(ShotgunQuery, self).update(*args)
        self.view_data['header'] = self.view_data[Qt.DisplayRole]
    
    def get_initial_children(self, init_state):
        for type_ in self.active_types:
            if type_ in init_state:
                entity = init_state[type_]
                yield self._child_tuple_from_entity(entity)
    
    def _child_tuple_from_entity(self, entity):
        
        labels = []
        for format_ in self.formats[entity['type']]:
            state = dict(self.state)
            state[entity['type']] = entity
            try:
                labels.append(format_.format(**state))
            except KeyError:
                labels.append('%r %% %r' % (format_, entity))
        
        groups = []
        if len(self.active_types) > 1:
            groups.append((
                '%s group' % entity['type'],
                {
                    Qt.DisplayRole: entity['type'] + 's',
                },
                {
                    'entity_type': entity['type'],
                }
            ))
        
        for i, label in enumerate(labels[:-1]):
            groups.append((
                '%s group' % label,
                {
                    Qt.DisplayRole: label
                }, {
                    '%s.%d' % (entity['type'], i): label
                }
            ))
        
        view_data = {
            Qt.DisplayRole: labels[-1],
            'groups': groups,
            'header': labels[-1]
        }
        
        if entity.get('step') and entity['step'].get('color'):
            color = QtGui.QColor.fromRgb(*(int(x) for x in entity['step']['color'].split(',')))
            for group in groups:
                group[1][Qt.DecorationRole] = color
            view_data[Qt.DecorationRole] = color
            
        if entity['type'] in self.icons:
            view_data[Qt.DecorationRole] = self.icons[entity['type']]
        
        new_state = dict(('ignore_%s' % other, True) for other in self.active_types)
        new_state[entity['type']] = entity
        
        return entity.cache_key, view_data, new_state
    
    def fetch_async_children(self, type_i=0):
        
        if type_i + 1 < len(self.active_types):
            self.schedule_async_fetch(self.fetch_async_children, type_i + 1)
        
        type_ = self.active_types[type_i]
        
        filters = []
        for backref in self.backrefs[type_]:
            if backref and backref[0] in self.state:
                filters.append((backref[1], 'is', self.state[backref[0]]))
        
        res = []
        for entity in sgfs.session.find(type_, filters, self.fields.get(type_) or []):
            res.append(self._child_tuple_from_entity(entity))
        
        # Sort by label.
        res.sort(key=lambda x: x[1][Qt.DisplayRole])
        
        return res



class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    
    def __init__(self, root_state=None):
        super(Model, self).__init__()
        
        self.root_state = root_state or {}
        self._root = None
        
        self.node_types = []
    
    def set_initial_state(self, init_state):
        if self._root is not None:
            raise ValueError('cannot set initial state with existing root')
        
        last_match = None
        nodes = [self.root()]
        while True:
            
            if not nodes:
                break
            
            node = nodes.pop(0)
            debug('node.matches_init_state: %s', repr(node))
            if node.matches_init_state(init_state):
                debug('matches: %r', node.state)
                last_match = node
            else:
                continue
            
            nodes.extend(node.children(init_state))

        if last_match:
            debug('last_match.state: %r', last_match.state)
            debug('last_match.index: %r', last_match.index)
            # for k, v in sorted(last_match.state.iteritems()):
            #    # debug('\t%s: %r', k, v)
            return last_match.index
    
    def construct_node(self, key, view_data, state):
        for node_type in self.node_types:
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
            self._root = self.construct_node(None, {}, self.root_state)
            self._root.index = QtCore.QModelIndex()
            self._root.parent = QtCore.QModelIndex()
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
            # debug('child.index is None: %r', child)
            child.index = self.createIndex(row, col, child)
            if child.parent is None:
                # debug('\tchild.parent is also None')
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
            
            if isinstance(data, basestring):
                return QtGui.QPixmap(data)
            
            return data
        
        # Passthrough other roles.
        try:
            return node.view_data[role]
        except KeyError:
            return QtCore.QVariant()



class Header(QtGui.QHeaderView):
    
    def __init__(self, node):
        super(Header, self).__init__(Qt.Horizontal)
        self._node = node
        self.setResizeMode(0, QtGui.QHeaderView.Fixed)
        self.setStretchLastSection(True)
        
    def paintEvent(self, e):
            
        # We need a horrible hack to get different headers in different columns.
        # Before every paint event we update the data that the model will
        # provide when requested in real painting implementation.
        
        if self._node.is_loading:
            header = 'Loading...'
        else:
            header = self._node.view_data.get('header', '')
        self.model()._header = header
        
        super(Header, self).paintEvent(e)


class HeaderedListView(QtGui.QTreeView):
    
    def __init__(self, model, index, node):
        super(HeaderedListView, self).__init__()
        
        # Take control over what is displayed in the header.
        self._header = Header(node)
        self.setHeader(self._header)
        
        # Make this behave like a fancier QListView. This also allows for the
        # right arrow to select.
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        
        self.setModel(model)
        self.setRootIndex(index)


class ColumnView(QtGui.QColumnView):
    
    def __init__(self):
        super(ColumnView, self).__init__()
        
        # A sensible default for Shotgun entities.
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        
        # State for setting preview visibility.
        self._widgetsize_max = None
        self._preview_visible = True
    
    def previewVisible(self):
        return self._preview_visible
    
    def setPreviewVisible(self, flag):
        
        flag = bool(flag)
        if flag == self._preview_visible:
            # No-Op.
            return
        
        self._preview_visible = flag
        
        if not flag:
            
            # We need there to be some preview widget to latch on to.
            widget = self.previewWidget()
            if not widget:
                widget = self._preview_sentinel = QtGui.QWidget()
                self.setPreviewWidget(widget)
                
            # The protected preview column owns the preview widget.
            column = widget.parent().parent()
            
            # We don't have access to this in macro form, so extract it from
            # the widget.
            if self._widgetsize_max is None:
                self._widgetsize_max = column.maximumWidth()
            
            # The actual hiding.
            column.setFixedWidth(0)
        
        else:
            widget = self.previewWidget()
            column = widget.parent().parent()
            column.setFixedWidth(self._widgetsize_max)
        
    
    def createColumn(self, index):
        
        # This method exists solely because we want headers in our list views,
        # and this was the only way I found to do it.
        
        node = self.model().node_from_index(index)
        view = HeaderedListView(self.model(), index, node)
        
        # Transfer standard behaviour and our options to the new column.
        self.initializeColumn(view)
        
        # We must hold a reference to this somewhere so that it isn't
        # garbage collected on us.
        node.__view = view
                
        return view
    
    def currentChanged(self, current, previous):
        super(ColumnView, self).currentChanged(current, previous)
        node = self.model().node_from_index(self.selectionModel().currentIndex())
        self.nodeChanged(node)

    def nodeChanged(self, node):
        self.stateChanged(node.state)
    
    def stateChanged(self, state):
        debug('stateChanged:\n%s\n', pprint.pformat(state))








def state_from_entity(entity):
    state = {}
    while entity and entity['type'] not in state:
        state[entity['type']] = entity
        entity = entity.parent()
    return state
        

    
if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    
    view_class = ColumnView
    
    if False:
        model = Model(state_from_entity(sgfs.session.get('Project', 74)))
    else:
        model = Model()
    
    model.node_types.append(SGFSRoots)
    # model.node_types.append(ShotgunProjectTopLevel)
    # 
    # if False:
    #     model.node_types.append(ShotgunSteps) # Must be before ShotgunTasks
    # 
    # model.node_types.append(ShotgunTasks)
    
    model.node_types.append(ShotgunQuery.specialize(('Asset', 'Sequence', 'Shot', 'Task', 'PublishEvent')))

    # model.node_types.append(ShotgunQuery.for_entity_type('Tool'        , ('Project', 'project'), '{code}', fields=['code']))
    # model.node_types.append(ShotgunQuery.for_entity_type('Ticket'        , ('Tool', 'sg_tool'), '{title}', fields=['title']))
    
    # model.node_types.append(ShotgunQuery.for_entity_type('Sequence'    , ('Project' , 'project'    ), '{code}', group_format='Sequence'))
    # model.node_types.append(ShotgunQuery.for_entity_type('Asset'       , ('Project' , 'project'    ), '{code}', group_format=('Asset', '{Asset[sg_asset_type]}')))
    # model.node_types.append(ShotgunQuery.for_entity_type('Shot'        , ('Sequence', 'sg_sequence'), '{code}'))
    #model.node_types.append(ShotgunQuery.for_entity_type('PublishEvent', ('Task'    , 'sg_link'    ), 'v{sg_version:04d}', group_format=('{PublishEvent[sg_type]}', '{PublishEvent[code]}')))


    type_ = None
    id_ = None
    
    if len(sys.argv) > 1:
    
        import sgfs.commands.utils as command_utils
        data = command_utils.parse_spec(sgfs, sys.argv[1:])
        
        type_ = data.get('type')
        id_ = data.get('id')
    
    if type_ and id_:
        
        print type_, id_
        entity = sgfs.session.get(type_, id_)
        
        init_state = {}
        while entity and entity['type'] not in init_state:
            init_state[entity['type']] = entity
            entity = entity.parent()

        print 'init_state', init_state
        print
    
        index = model.set_initial_state(init_state)

        view = view_class()
        view.setModel(model)
        if index:
            # debug('selecting %r -> %r', index, model.node_from_index(index))
            view.setCurrentIndex(index)

    else:
        
        print 'no entity specified'
        
        view = view_class()
        view.setModel(model)
    
    # view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    view.setFixedWidth(800)
    view.setColumnWidths([200] * 10) # To be sure that the width is 2 more.
    # view.setResizeGripsVisible(False)

    view.setPreviewVisible(False)

    dialog = QtGui.QDialog()
    dialog.setWindowTitle(sys.argv[0])
    dialog.setLayout(QtGui.QVBoxLayout())
    dialog.layout().addWidget(view)
    
    dialog.show()
    dialog.raise_()

    exit(app.exec_())
