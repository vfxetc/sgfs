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
    def is_next_node(state, goal_state):
        return True
    
    def __init__(self, model, parent, view_data, state, goal_state=None):
        
        if not self.is_next_node(state, goal_state):
            raise KeyError('not next state')
        
        self.model = model
        self.parent = parent
        
        self.view_data = view_data or {}
        self.state = state
        self.goal_state = goal_state
        
        self.index = None
        
        self._children = None
        self._child_lock = threading.Lock()
    
    def has_children(self):
        return True
    
    def get_child_from_goal(self):
        return None
    
    def get_children(self):
        
        try:
            async = self.get_children_async
        except AttributeError:
            raise NotImplementedError()
        
        future = threadpool.submit(async)
        future.add_done_callback(lambda f: self.update_children(f.result()))
        
        return []
    
    def update_children(self, new_children):
        
        children = []
        for key, view_data, new_state in new_children:
            child_state = dict(self.state)
            child_state.update(new_state)
            child = self.model.construct_node(self, view_data, child_state, self.goal_state)
            children.append(child)
        
        signal = self.index is not None and self._children is not None
        
        if signal:
            self.model.beginInsertRows(self.index, 0, len(children))
        
        self._children = children
        
        if signal:
            self.model.endInsertRows()
    
    def children(self):
        with self._child_lock:
            if self._children is None:
                self.update_children(self.get_children())
            return self._children


class LeafNode(Node):

    def __init__(self, *args):
        super(LeafNode, self).__init__(*args)
        self.view_data['header'] = 'LEAF'
    
    def has_children(self):
        return False
    
    def get_children(self):
        return []


class SGFSRoots(Node):
    
    @staticmethod
    def is_next_node(state, goal_state):
        return 'Project' not in state and (goal_state is None or 'Project' in goal_state)
    
    def get_children(self):
        for project, path in sorted(sgfs.project_roots.iteritems(), key=lambda x: x[0]['name']):
            yield project.cache_key, {Qt.DisplayRole: project['name']}, {
                'Project': project,
                'Project.path': path,
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
    def is_next_node(cls, state, goal_state):
        return (
            cls.entity_type not in state and # Avoid cycles.
            (cls.backref is None or cls.backref[0] in state) and # Has backref.
            (goal_state is None or cls.entity_type in goal_state) # Match goal.
        )
    
    def __init__(self, *args):
        super(ShotgunQuery, self).__init__(*args)
        self.view_data['header'] = self.entity_type
    
    def get_children_async(self):
        
        # Apply backref filter.
        filters = []
        if self.backref is not None:
            filters.append((self.backref[1], 'is', self.state[self.backref[0]]))
        
        res = []
        for entity in sgfs.session.find(self.entity_type, filters, ['step.Step.color']):
            
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
            
            res.append((
                entity.cache_key, # Key.
                view_data,
                {entity['type']: entity}, # New state.
            ))
        
        return res


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    
    def __init__(self):
        super(Model, self).__init__()
        
        self._root = None
        self.node_types = []
    
    def set_initial_state(self, goal_state):
        if self._root is not None:
            raise ValueError('cannot set initial state with existing root')
        
        nodes = [self.root(goal_state)]
        leafs = []
        while True:
            
            leafs.extend(x for x in nodes if isinstance(x, LeafNode))
            nodes = [x for x in nodes if not isinstance(x, LeafNode)]
            if not nodes:
                break
            
            node = nodes.pop()
            print 'checking', node
            nodes.extend(node.children())
        
        print leafs
        
    
    def construct_node(self, parent, view_data, state, goal_state=None):
        for node_type in self.node_types:
            try:
                return node_type(self, parent, view_data, state, goal_state)
            except KeyError:
                pass
        print "Leaf", state
        return LeafNode(self, parent, view_data, state)
        
    def hasChildren(self, index):
        node = self.node_from_index(index)
        return node.has_children()
    
    def root(self, goal_state=None):
        if self._root is None:
            self._root = self.construct_node(None, {}, {}, goal_state)
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
    print 'setting', shot
    shot.fetch_heirarchy()

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
