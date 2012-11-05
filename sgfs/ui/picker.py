# import gevent.monkey
# gevent.monkey.patch_socket()

import sys
import os

import concurrent.futures

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

app = QtGui.QApplication(sys.argv)
sgfs = SGFS()

threadpool = concurrent.futures.ThreadPoolExecutor(4)

# sys.path.append('/home/mboers/Documents/RemoteConsole')
# import remoteconsole 
# remoteconsole.spawn(('', 12345), globals())


heirarchy = {
    'Project': ('Sequence', 'project'),
    'Sequence': ('Shot', 'sg_sequence'),
    'Shot': ('Task', 'entity'),
    'Task': ('PublishEvent', 'sg_link'),
}

entity_name = {
    'Project': '{name}',
    'Sequence': '{code}',
    'Asset': '{code}',
    'Shot': '{code}',
    'Task': '{step[short_name]} - {content}',
    'PublishEvent': '{code} ({sg_type}) at {sg_version}',
}


class TextOption(object):

    def __init__(self, key, *options):
        self.key = key
        self.options = options
    
    def __call__(self, data):
        for option in self.options:
            yield option, {self.key: option}





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
        
        self.index = None # Set by the model.
        
        self.is_loading = False
        self._children = None
    
    def has_children(self):
        return True
    
    def fetch_children(self):
        raise NotImplementedError()
    
    def update_children(self, new_children, signal=True):
        
        children = []
        for view_data, new_state in new_children:
            child_state = dict(self.state)
            child_state.update(new_state)
            child = self.model.get_next_node(self, view_data, child_state)
            children.append(child)
        
        if signal:
            self.model.beginInsertRows(self.index, 0, len(children))
        
        self._children = children
        
        if signal:
            self.model.endInsertRows()
    

    def children(self):
        if self._children is None:
            self.update_children(self.fetch_children(), signal=False)
        return self._children


class LeafNode(Node):

    def __init__(self, *args):
        super(LeafNode, self).__init__(*args)
        self.view_data['header'] = ''
    
    def has_children(self):
        return False
    
    def fetch_children(self):
        return []


class ShotgunQuery(Node):
    
    entity_type = 'Project'
    backref = (None, None)
    
    @classmethod
    def build_basic(cls, entity_type, backref):
        class Specialized(cls):
            pass
        Specialized.__name__ = '%s%s' % (entity_type, cls.__name__)
        Specialized.entity_type = entity_type
        Specialized.backref = backref
        return Specialized
    
    @classmethod
    def is_next_node(cls, state, goal_state):
        if cls.entity_type not in state and (cls.backref is None or cls.backref[0] in state):
            if goal_state is not None and cls.entity_type not in goal_state:
                return False
            return True
        return False
    
    def __init__(self, *args):
        super(ShotgunQuery, self).__init__(*args)
        self.view_data['header'] = self.entity_type
    
    def fetch_children(self):
        print 'fetching children'
        future = threadpool.submit(self._fetch_children)
        future.add_done_callback(lambda f: self.update_children(f.result()))
        return []
    
    def _fetch_children(self):
        filters = []
        if self.backref is not None:
            filters.append((self.backref[1], 'is', self.state[self.backref[0]]))
        
        for entity in sgfs.session.find(self.entity_type, filters):

            print 'have', entity
            try:
                label = entity_name[entity['type']].format(**entity)
            except KeyError:
                label = repr(entity)
                
            view_data = {
                Qt.DisplayRole: label,
            }
            
            yield view_data, {entity['type']: entity}


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    
    def __init__(self):
        super(Model, self).__init__()
        
        self._root = None
        self.node_types = []
    
    def get_next_node(self, parent, view_data, state):
        for node_type in self.node_types:
            try:
                return node_type(self, parent, view_data, state)
            except KeyError:
                pass
        return LeafNode(self, parent, view_data, state)
        
    def hasChildren(self, index):
        node = self.node_from_index(index)
        return node.has_children()
        
        
    def _get_iter(self, data):
        
        if 'Task' in data:
            return ShotgunQuery('PublishEvent', [('sg_link', 'is', data['Task'])])

        if 'Shot' in data:
            return ShotgunQuery('Task', [('entity', 'is', data['Shot'])])
            
        if 'Asset' in data:
            return ShotgunQuery('Task', [('entity', 'is', data['Asset'])])
        
        if 'Sequence' in data:
            return ShotgunQuery('Shot', [('sg_sequence', 'is', data['Sequence'])])
        
        if 'asset_type' in data:
            return ShotgunQuery('Asset', [
                ('project', 'is', data['Project']),
                ('sg_asset_type', 'is', data['asset_type']),
            ])
            
        if data.get('entity_type') == 'Sequences':
            return ShotgunQuery('Sequence', [('project', 'is', data['Project'])])
            
        if data.get('entity_type') == 'Assets':
            project_dir = sgfs.path_for_entity(data['Project'])
            asset_types = os.listdir(os.path.join(project_dir, 'Assets'))
            asset_types = [x for x in asset_types if not x.startswith('.')]
            return TextOption('asset_type', *asset_types)
        
        if 'Project' in data:
            return TextOption('entity_type', 'Assets', 'Sequences')
        
        if not data:
            return lambda data: [(x['name'], {'Project': x}) for x in sgfs.project_roots]
        
        print 'Cant do anything with %r' % data
        return None
    
    def root(self):
        if self._root is None:
            self._root = self.get_next_node(None, {}, {})
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
        return len(node.children()) if node is not None else 0
    
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
        
    # def flags(self, index):
    #     if not index.row():
    #         return Qt.NoItemFlags
    #     return super(Model, self).flags(index)
    
    def data(self, index, role):
        
        if not index.isValid():
            return QtCore.QVariant()
        
        if role == Qt.DisplayRole:
            node = self.node_from_index(index)
            return node.view_data.get(Qt.DisplayRole, repr(node))
        
        # if role == Qt.DecorationRole:
        #     return QtGui.QColor(256, 128, 64)
        
        else:
            # Invalid variant.
            return QtCore.QVariant()


_views = []



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
        
        # Make this behave like a fancier ListView. This also allows for the
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
        header = node.view_data.get('header', 'No Header')

        view = TreeView(self.model(), index, header)
        
        view.setTextElideMode(Qt.ElideMiddle)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
        _views.append(view)
                
        return view
        


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self.setWindowTitle(sys.argv[0])
        


obj = ColumnView()

model = Model()
model.node_types.append(ShotgunQuery.build_basic('Project', None))
model.node_types.append(ShotgunQuery.build_basic('Sequence', ('Project', 'project')))
model.node_types.append(ShotgunQuery.build_basic('Shot', ('Sequence', 'sg_sequence')))
model.node_types.append(ShotgunQuery.build_basic('Task', ('Shot', 'entity')))


obj.setModel(model)

obj.show()
obj.raise_()

exit(app.exec_())
