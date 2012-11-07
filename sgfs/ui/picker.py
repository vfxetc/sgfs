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


class DummyLock(object):
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class Node(object):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def __init__(self, model, key, view_data, state):
        
        if not self.is_next_node(state):
            raise KeyError('not next state')
        
        self.model = model
        self.key = key
        
        self.view_data = None
        self.state = None
        self.update(view_data or {}, state or {})
        
        # These are set by the model.
        self.index = None
        self.parent = None
        
        self._child_lock = DummyLock() if False else threading.RLock()
        self._children = None
        self.is_loading = False
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def update(self, view_data, state):
        self.view_data = view_data
        self.state = state
    
    def has_children(self):
        return True
    
    def matches_goal(self, init_state):
        try:
            return all(init_state[k] == v for k, v in self.state.iteritems())
        except KeyError:
            pass
    
    def fetch_children(self, init_state):
        
        debug('fetch_children')
        
        if hasattr(self, 'fetch_async_children'):
            self.is_loading = True
            threadpool.submit(self._fetch_async_children)
            # threading.Thread(target=self._fetch_async_children).start()
        
        # Return any children we can figure out from the init_state.
        if init_state is not None and self.matches_goal(init_state):
            return self.get_immediate_children_from_goal(init_state) or []
        
        return []
        
    def _fetch_async_children(self):
        
        try:
            
            # Since async may be a generator, for it to completion before we grab
            # the update lock.
            children = list(self.fetch_async_children())
        
            debug('2nd fetch_children (async) is done')
        
            # This forces the update to wait until after the first (static) children
            # have been put into place, even if this function runs very quickly.
            with self._child_lock:
                debug('2nd replace_children (async)')
                self.is_loading = False
                self._update_children(children)
        
        except Exception as e:
            traceback.print_exc()
            raise
        
    def get_immediate_children_from_goal(self, init_state):
        """Return temporary children that we can from the given init_state, so
        that there is something there while we load the real children."""
        return []
    
    def _update_children(self, updated):
        
        signal = self.index is not None and self._children is not None
        if signal:
            debug('    layoutAboutToBeChanged')
            self.model.layoutAboutToBeChanged.emit()
        
        self._children = self._children or ChildList()
        
        for key, view_data, new_state in updated:
            
            full_state = dict(self.state)
            full_state.update(new_state)
            
            # Update old nodes if we have them.
            node = self._children.pop(key, None)
            if node is not None:
                node.update(view_data, full_state)
            else:
                node = self.model.construct_node(key, view_data, full_state)
                node.parent = self
                
            self._children.append(node)
        
        
        # (Re)Set all of the indexes.
        old_indexes = []
        new_indexes = []
        for i, child in enumerate(self._children):
            
            if child.index is None:
                child.index = self.model.createIndex(i, 0, child)
            
            else:
                old_indexes.append(child.index)
                child.index = self.model.createIndex(i, 0, child)
                new_indexes.append(child.index)
            
        if old_indexes:
            self.model.changePersistentIndexList(old_indexes, new_indexes)
        
        if signal:
            debug('    layoutChanged')
            self.model.layoutChanged.emit()
        
        
        
    
    def children(self, init_state=None):
        with self._child_lock:
            if self._children is None:
                debug('1st fetch_children')
                initial_children = list(self.fetch_children(init_state))
                debug('1st replace_children')
                self._update_children(initial_children)
            return self._children


class Leaf(Node):
    
    def has_children(self):
        return False
    
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
    
    @classmethod
    def for_entity_type(cls, entity_type, backref=None, display_format='{type} {id}'):
        return functools.partial(cls,
            entity_type=entity_type,
            backref=backref,
            display_format=display_format,
        )
    
    def __init__(self, *args, **kwargs):
        self.entity_type = kwargs.pop('entity_type', 'Project')
        self.backref = kwargs.pop('backref', None)
        self.display_format = kwargs.pop('display_format', '{name}')
        super(ShotgunQuery, self).__init__(*args, **kwargs)
    
    def __repr__(self):
        return '<%s for %r at 0x%x>' % (self.__class__.__name__, self.entity_type, id(self))
    
    def is_next_node(self, state):
        return (
            self.entity_type not in state and # Avoid cycles.
            (self.backref is None or self.backref[0] in state) # Has backref.
        )
    
    def update(self, *args):
        super(ShotgunQuery, self).update(*args)
        self.view_data['header'] = self.entity_type
    
    def get_immediate_children_from_goal(self, init_state):
        if self.entity_type in init_state:
            entity = init_state[self.entity_type]
            return [self._child_tuple(entity)]
    
    def _child_tuple(self, entity):
        
        try:
            display_role = self.display_format.format(**entity)
        except KeyError:
            display_role = repr(entity)
            
        view_data = {
            Qt.DisplayRole: display_role,
            Qt.DecorationRole: {
                'Sequence': '/home/mboers/Documents/icons/fatcow/16x16/film_link.png',
                'Shot': '/home/mboers/Documents/icons/fatcow/16x16/film.png',
                'Task': '/home/mboers/Documents/icons/fatcow/16x16/to_do_list.png',
                'PublishEvent': '/home/mboers/Documents/icons/fatcow/16x16/brick.png',
                'Asset': '/home/mboers/Documents/icons/fatcow/16x16/box_closed.png',
            }.get(entity['type'])
        }
            
        return (
            entity.cache_key, # Key.
            view_data,
            {entity['type']: entity}, # New state.
        )
        
    def fetch_async_children(self):
        
        # Apply backref filter.
        filters = []
        if self.backref is not None:
            filters.append((self.backref[1], 'is', self.state[self.backref[0]]))
        
        res = []
        for entity in sgfs.session.find(self.entity_type, filters, ['step.Step.color']):
            # debug('\t%r', entity)
            res.append(self._child_tuple(entity))
        
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
            debug('node.matches_goal: %s', repr(node))
            if node.matches_goal(init_state):
                debug('matches: %r', node.state)
                last_match = node
            else:
                continue
            
            nodes.extend(node.children(init_state))

        if last_match:
            debug('last_match.state: %r', last_match.state)
            debug('last_match.index: %r', last_match.index)
            # for k, v in sorted(last_match.state.iteritems()):
            #    debug('\t%s: %r', k, v)
            return last_match.index
    
    def construct_node(self, key, view_data, state):
        for node_type in self.node_types:
            try:
                return node_type(self, key, view_data, state)
            except KeyError:
                pass
        return Leaf(self, key, view_data, state)
        
    def hasChildren(self, index):
        node = self.node_from_index(index)
        res = node.has_children()
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
            # This is set by the TreeView widgets as they are being painted.
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
        
        # self._timer = QtCore.QTimer()
        # self._timer.singleShot(1000, self._upper_header)
    
    def _upper_header(self, *args):
        self._name = self._name.upper()
        self.model().headerDataChanged.emit(Qt.Horizontal, 0, 0)
        
    def paintEvent(self, e):

        # Such a horrible hack.
        if self._node.is_loading:
            header = 'Loading...'
        else:
            header = self._node.view_data.get('header', '')
        self.model()._header = header
        
        super(Header, self).paintEvent(e)


class TreeView(QtGui.QTreeView):
    
    def __init__(self, model, index, node):
        super(TreeView, self).__init__()
        
        self._header = Header(node)
        self.setHeader(self._header)
        
        self.setModel(model)
        self.setRootIndex(index)
        
        # Make this behave like a fancier QListView. This also allows for the
        # right arrow to select.
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)


class ColumnView(QtGui.QColumnView):
    
    def __init__(self):
        super(ColumnView, self).__init__()
        
        # self.setMinimumWidth(800)
        # self.setColumnWidths([200, 150, 150, 170, 200, 400] + [150] * 20)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        
        self._widgetsize_max = None
        self._preview_visible = True
    
    def previewVisible(self):
        return self._preview_visible
    
    def setPreviewVisible(self, flag):
        
        flag = bool(flag)
        
        # debug('setPreviewVisible: %r', flag)
        
        # No-op.
        if flag == self._preview_visible:
            return
        
        # Hide it.
        if not flag:
            
            # We need there to be some preview widget.
            widget = self.previewWidget()
            if not widget:
                widget = self._preview_sentinel = QtGui.QWidget()
                # widget.setFixedSize(0, 0)
                self.setPreviewWidget(widget)
                
            # The protected preview column owns the preview widget.
            column = widget.parent().parent()
            
            # We don't have access to this in macro form, so extract it from
            # the widget.
            if self._widgetsize_max is None:
                self._widgetsize_max = column.maximumWidth()
            
            # The actual hiding.
            column.setFixedWidth(0)
        
        # Show it.
        else:
            widget = self.previewWidget()
            column = widget.parent().parent()
            column.setFixedWidth(self._widgetsize_max)
        
        self._preview_visible = flag
    
    def createColumn(self, index):
        
        node = self.model().node_from_index(index)        
        view = TreeView(self.model(), index, node)
        
        # Transfer behaviour and options to the new column.
        self.initializeColumn(view)
        
        # We must hold a reference to this somewhere so that it isn't
        # garbage collected on us.
        node.__view = view
                
        return view
    
    def currentChanged(self, current, previous):
        super(ColumnView, self).currentChanged(current, previous)
        x = self.model().node_from_index(self.selectionModel().currentIndex())
        debug('currentChanged to %r', x)






        


class ShotgunSteps(Node):
    
    def is_next_node(self, state):
        if 'Step' in state:
            return
        for x in ('Shot', 'Asset'):
            if x in state:
                self.entity_type = x
                return True
    
    def update(self, view, state):
        super(ShotgunSteps, self).update(view, state)
        self.view_data['header'] = 'Pipeline Step'
        
    def fetch_async_children(self):
        
        # Get the tasks.
        tasks_by_step = {}
        for task in sgfs.session.find('Task', [('entity', 'is', self.state[self.entity_type])], ['step.Step.color']):
            tasks_by_step.setdefault(task['step'], []).append(task)
        
        for step, tasks in sorted(tasks_by_step.iteritems(), key=lambda x: x[0]['code']):
            yield (
                step.cache_key,
                {
                    Qt.DisplayRole: ('%s (%d)' % (step['code'], len(tasks))),
                    Qt.DecorationRole: QtGui.QColor.fromRgb(*[int(x) for x in step['color'].split(',')]),
                }, {
                    'Step': step,
                    'Step.tasks': tasks
                }
            )
    

class ShotgunTasks(ShotgunQuery):
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('display_format', '{content}')
        super(ShotgunTasks, self).__init__(*args, **kwargs)
        self.entity_type = 'Task'
        self.backref = (self.task_entity_type, 'entity')
    
    def update(self, view, state):
        super(ShotgunTasks, self).update(view, state)
        if 'Step' in self.state:
            self.view_data['header'] = '%s Task' % self.state['Step']['short_name']
        else:
            self.view_data['header'] = 'Task'
        
    def is_next_node(self, state):
        if 'Task' in state:
            return
        for x in ('Shot', 'Asset'):
            if x in state:
                self.task_entity_type = x
                return True
    
    def fetch_async_children(self):
        
        # Shortcut!
        entities = self.state.get('Step.tasks')
        if entities is None:
            entities = list(sgfs.session.find('Task', [('entity', 'is', self.state[self.task_entity_type])], ['step.Step.color']))
        
        res = []
        for entity in entities:
            key, view, state = self._child_tuple(entity)
            if 'Step' not in self.state:
                view[Qt.DecorationRole] = QtGui.QColor.fromRgb(*[int(x) for x in entity['step']['color'].split(',')])
            res.append((key, view, state))
        
        res.sort(key=lambda t: t[1][Qt.DisplayRole])
        return res

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
        model = Model(state_from_entity(sgfs.session.get('Sequence', 113)))
    else:
        model = Model()
    
    model.node_types.append(SGFSRoots)
    

    if False:
        model.node_types.append(ShotgunSteps) # Must be before ShotgunTasks
    
    model.node_types.append(ShotgunTasks)
    
    
    
    model.node_types.append(ShotgunQuery.for_entity_type('Sequence'    , ('Project' , 'project'    ), '{code}'))
    model.node_types.append(ShotgunQuery.for_entity_type('Shot'        , ('Sequence', 'sg_sequence'), '{code}'))
    model.node_types.append(ShotgunQuery.for_entity_type('PublishEvent', ('Task'    , 'sg_link'    ), '{code} ({sg_type}/{sg_version})'))


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
            debug('selecting %r -> %r', index, model.node_from_index(index))
            view.setCurrentIndex(index)

    else:
        
        print 'no entity specified'
        
        view = view_class()
        view.setModel(model)
    
    # view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    view.setFixedWidth(800)
    view.setColumnWidths([200, 200, 398]) # To be sure that the width is 2 more.
    # view.setResizeGripsVisible(False)

    view.setPreviewVisible(False)

    dialog = QtGui.QDialog()
    dialog.setWindowTitle(sys.argv[0])
    dialog.setLayout(QtGui.QVBoxLayout())
    dialog.layout().addWidget(view)
    
    dialog.show()
    dialog.raise_()

    exit(app.exec_())
