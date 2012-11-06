# import gevent.monkey
# gevent.monkey.patch_socket()

import sys
import os
import random
import threading

import concurrent.futures

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

app = QtGui.QApplication(sys.argv)
sgfs = SGFS()

threadpool = concurrent.futures.ThreadPoolExecutor(8)

# sys.path.append('/home/mboers/Documents/RemoteConsole')
# import remoteconsole 
# remoteconsole.spawn(('', 12345), globals())








class Node(object):
    
    @staticmethod
    def is_next_node(state):
        return True
    
    def __init__(self, model, parent, view_data, state):
        
        if not self.is_next_node(state):
            raise KeyError('not next state')
        
        self.model = model
        self.parent = parent
        
        self.view_data = view_data or {}
        self.state = state
        
        self.index = None
        
        self._child_map = {}
        self._child_list = None
        self._child_lock = threading.Lock()
    
    def has_children(self):
        return True
    
    def matches_goal(self, goal_state):
        try:
            return all(goal_state[k] == v for k, v in self.state.iteritems())
        except KeyError:
            pass
        
    def get_child_from_goal(self, goal_state):
        return None
    
    def get_children(self, goal_state=None):
        
        try:
            async = lambda: list(self.get_children_async())
        except AttributeError:
            raise NotImplementedError()
        
        future = threadpool.submit(async)
        future.add_done_callback(lambda f: self.update_children(f.result()))
        
        if goal_state is not None and all(goal_state.get(k) == v for k, v in self.state.iteritems()):
            child = self.get_child_from_goal(goal_state)
            if child:
                return [child]
        
        return []
    
    def update_children(self, new_children):
        
        child_map = {}
        child_list = []
        
        for key, view_data, new_state in new_children:
            child_state = dict(self.state)
            child_state.update(new_state)
            child = self.model.construct_node(self, view_data, child_state)
            
            child_map[key] = len(child_list)
            child_list.append(child)
        
        signal = self.index is not None and self._child_list is not None
        
        if signal:
            self.model.beginInsertRows(self.index, 0, len(child_list))
        
        self._child_map = child_map
        self._child_list = child_list
        
        if signal:
            self.model.endInsertRows()
    
    def children(self, goal_state=None):
        with self._child_lock:
            if self._child_list is None:
                self.update_children(self.get_children(goal_state))
            return self._child_list


class Leaf(Node):

    def __init__(self, *args):
        super(Leaf, self).__init__(*args)
        self.view_data['header'] = 'LEAF'
    
    def has_children(self):
        return False
    
    def get_children(self, goal_state=None):
        return []


class SGFSRoots(Node):
    
    @staticmethod
    def is_next_node(state):
        return 'Project' not in state
    
    def get_children(self, goal_state=None):
        for project, path in sorted(sgfs.project_roots.iteritems(), key=lambda x: x[0]['name']):
            yield project.cache_key, {Qt.DisplayRole: project['name']}, {
                'Project': project,
            }
            
    
    
class ShotgunQuery(Node):
    
    entity_type = 'Project'
    backref = None
    display_format = '{name}'
    
    @classmethod
    def for_entity_type(cls, entity_type, backref=None, display_format='{type} {id}'):
        class Specialized(cls):
            pass
        Specialized.__name__ = '%s%s' % (entity_type, cls.__name__)
        Specialized.entity_type = entity_type
        Specialized.backref = backref
        Specialized.display_format = display_format
        return Specialized
    
    @classmethod
    def is_next_node(cls, state):
        return (
            cls.entity_type not in state and # Avoid cycles.
            (cls.backref is None or cls.backref[0] in state) # Has backref.
        )
    
    def __init__(self, *args):
        super(ShotgunQuery, self).__init__(*args)
        self.view_data['header'] = self.entity_type
    
    def get_child_from_goal(self, goal_state):
        if self.entity_type in goal_state:
            entity = goal_state[self.entity_type]
            return self._child_tuple(entity)
    
    def _child_tuple(self, entity):
        try:
            label = self.display_format.format(**entity)
        except KeyError:
            label = repr(entity)
            
        view_data = {
            Qt.DisplayRole: label,
        }
            
        # Apply step colour decoration.
        if 'step' in entity and 'color' in entity['step']:
            view_data[Qt.DecorationRole] = QtGui.QColor.fromRgb(*[int(x) for x in entity['step']['color'].split(',')])
            
        return (
            entity.cache_key, # Key.
            view_data,
            {entity['type']: entity}, # New state.
        )
        
    def get_children_async(self):
        
        # Apply backref filter.
        filters = []
        if self.backref is not None:
            filters.append((self.backref[1], 'is', self.state[self.backref[0]]))
        
        for entity in sgfs.session.find(self.entity_type, filters, ['step.Step.color']):
            yield self._child_tuple(entity)
            
        


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    
    def __init__(self):
        super(Model, self).__init__()
        
        self._root = None
        self.node_types = []
    
    def set_initial_state(self, goal_state):
        if self._root is not None:
            raise ValueError('cannot set initial state with existing root')
        
        last_match = None
        nodes = [self.root()]
        while True:
            
            if not nodes:
                break
            
            node = nodes.pop()
            if node.matches_goal(goal_state):
                last_match = node
            else:
                continue
            
            print 'searching', node.state
            for child in node.children(goal_state):
                print '\t', child.state
                for k, v in child.state.iteritems():
                    if goal_state.get(k) != v:
                        print '\t\tfailed on %s' % k
                        break
                else:
                    nodes.append(child)
        
        print 'last match was', last_match
        if last_match:
            for k, v in sorted(last_match.state.iteritems()):
                print '\t%s: %r' % (k, v)
    
    def construct_node(self, parent, view_data, state):
        for node_type in self.node_types:
            try:
                return node_type(self, parent, view_data, state)
            except KeyError:
                pass
        return Leaf(self, parent, view_data, state)
        
    def hasChildren(self, index):
        node = self.node_from_index(index)
        return node.has_children()
    
    def root(self):
        if self._root is None:
            self._root = self.construct_node(None, {}, {})
            self._root.index = QtCore.QModelIndex()
        return self._root
    
    def node_from_index(self, index):
        if not index.isValid():
            return self.root()
        else:
            return index.internalPointer()
            
    def headerData(self, section, orientation, role):
        
        if role == Qt.DisplayRole:
            # This is set by the TreeView widgets as they are being painted.
            # I.e.: This is a huge hack.
            return self._header
        
        return QtCore.QVariant()
    
    def rowCount(self, parent):
        node = self.node_from_index(parent)
        return len(node.children())
    
    def columnCount(self, parent):
        return 1
    
    def index(self, row, col, parent):
        
        if col > 0:
            return QtCore.QModelIndex()
        
        node = self.node_from_index(parent)
        node_children = node.children()
        
        if row >= len(node_children):
            return QtCore.QModelIndex()
        
        child = node_children[row]
        index = self.createIndex(row, col, node_children[row])
        child.index = index
        return index
    
    def parent(self, child):

        node = self.node_from_index(child)
        if node.parent is None:
            return QtCore.QModelIndex()
        
        return node.parent.index
    
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
    
    def __init__(self, name):
        super(Header, self).__init__(Qt.Horizontal)
        self._name = name
        self.setResizeMode(0, QtGui.QHeaderView.Fixed)
        self.setStretchLastSection(True)
        
        # self._timer = QtCore.QTimer()
        # self._timer.singleShot(1000, self._upper_header)
    
    def _upper_header(self, *args):
        print '_upper_header', args
        self._name = self._name.upper()
        self.model().headerDataChanged.emit(Qt.Horizontal, 0, 0)
        
    def paintEvent(self, e):
        # Such a horrible hack.
        self.model()._header = self._name
        super(Header, self).paintEvent(e)


class TestDelegate(QtGui.QStyledItemDelegate):
    
    def __init__(self):
        super(TestDelegate, self).__init__()
        self._pixmap = QtGui.QPixmap('/home/mboers/Documents/icons/fatcow/32x32/3d_glasses.png')
    
    def sizeHint(self, option, index):
        hint = super(TestDelegate, self).sizeHint(option, index)
        hint.setHeight(hint.height() + self._pixmap.height())
        return hint
    
    def paint(self, painter, option, index):
        option.displayAlignment = Qt.AlignTop
        super(TestDelegate, self).paint(painter, option, index)
        painter.drawPixmap(
            (option.rect.width() - self._pixmap.width()) / 2,
            option.rect.height() - self._pixmap.height(),
            self._pixmap
        )


class TreeView(QtGui.QTreeView):
    
    def __init__(self, model, index, header):
        super(TreeView, self).__init__()
        
        self._header = Header(header)
        self.setHeader(self._header)
        
        self.setModel(model)
        self.setRootIndex(index)
        
        # Make this behave like a fancier QListView. This also allows for the
        # right arrow to select.
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)

        # self._delegate = TestDelegate()
        # self.setItemDelegateForRow(0, self._delegate)


class ColumnView(QtGui.QColumnView):
    
    def __init__(self):
        super(ColumnView, self).__init__()
        self.setMinimumWidth(800)
        self.setColumnWidths([200, 150, 150, 120, 400] + [150] * 20)
    
    def createColumn(self, index):
        
        node = self.model().node_from_index(index)
        header = node.view_data.get('header', '')

        view = TreeView(self.model(), index, header)
        
        # Look like the default QListView if we don't override createColumn.
        view.setTextElideMode(Qt.ElideMiddle)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # We must hold a reference to this somewhere so that it isn't
        # garbage collected on us.
        node.__view = view
                
        return view
    
    def currentChanged(self, current, previous):
        super(ColumnView, self).currentChanged(current, previous)
        x = self.selectionModel().currentIndex()
        print 'currentChanged', x.internalPointer().state if x.isValid() else None
        


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self.setWindowTitle(sys.argv[0])
        





model = Model()
model.node_types.append(SGFSRoots) # Defaults to Project level.
model.node_types.append(ShotgunQuery.for_entity_type('Sequence'    , ('Project' , 'project'    ), '{code}'))
model.node_types.append(ShotgunQuery.for_entity_type('Shot'        , ('Sequence', 'sg_sequence'), '{code}'))
model.node_types.append(ShotgunQuery.for_entity_type('Task'        , ('Shot'    , 'entity'     ), '{step[short_name]} - {content}'))
model.node_types.append(ShotgunQuery.for_entity_type('PublishEvent', ('Task'    , 'sg_link'    ), '{code} ({sg_type}/{sg_version})'))

if False:
    entity = shot = sgfs.session.get('Shot', 5887)
    print 'shot', shot
    goal_state = {}
    while entity and entity['type'] not in goal_state:
        goal_state[entity['type']] = entity
        entity = entity.parent()

    print 'goal_state', goal_state

    model.set_initial_state(goal_state)


obj = ColumnView()
obj.setModel(model)


obj.show()
obj.raise_()

exit(app.exec_())
