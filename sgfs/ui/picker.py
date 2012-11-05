# import gevent.monkey
# gevent.monkey.patch_socket()

import sys
import os

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

app = QtGui.QApplication(sys.argv)
sgfs = SGFS()


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


class ShotgunQuery(object):

    def __init__(self, *args):
        self.args = args
        
    
    def __call__(self, data):
        for entity in sgfs.session.find(*self.args):
            try:
                label = entity_name[entity['type']].format(**entity)
            except KeyError:
                label = repr(entity)
            yield label, {entity['type']: entity}


class Node(object):
    
    def __init__(self, parent, label, data, child_iter_func=None):
        self.parent = parent
        self.label = label
        self.data = data
        self.child_iter_func = child_iter_func
        self.child_iter_called = False
    
    def children(self):
        if not self.child_iter_called:
            self.child_iter_called = True
            self._children = []
            
            if self.child_iter_func:
                for label, new_data in self.child_iter_func(self.data):
                    child_data = dict(self.data)
                    child_data.update(new_data)
                    self._children.append(Node(self, label, child_data, model._get_iter(child_data)))
            
            self._children = tuple(self._children)
        return self._children


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Header Not Set'
    
    def __init__(self):
        super(Model, self).__init__()
        
        self._root = None
    
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
            self._root = Node(None, '', {}, self._get_iter({}))
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
        
    def hasChildren(self, parent):
        return True
    
    def rowCount(self, parent):
        
        node = self.node_from_index(parent)
        return len(node.children())
    
    def columnCount(self, parent):
        return 1
    
    def index(self, row, col, parent):
        
        if col > 0:
            return QtCore.QModelIndex()
        
        node = self.node_from_index(parent)
        node.index = parent
        node_children = node.children()
        
        if row >= len(node_children):
            return QtCore.QModelIndex()
        
        return self.createIndex(row, col, node_children[row])
    
    def parent(self, child):

        node = self.node_from_index(child)
        if node.parent is None:
            return QtCore.QModelIndex()
        
        return node.parent.index
        
    
    def data(self, index, role):
        
        if not index.isValid():
            return QtCore.QVariant()
        
        if role == Qt.DisplayRole:
            node = self.node_from_index(index)
            return node.label
        
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
        
    def paintEvent(self, e):
        # Such a horrible hack.
        self.model()._header = self._name
        super(Header, self).paintEvent(e)


class TreeView(QtGui.QTreeView):
    
    def __init__(self, model, index, header):
        super(TreeView, self).__init__()
        
        self._header = Header(header)
        self.setHeader(self._header)
        
        self.setModel(model)
        self.setRootIndex(index)
        
        
        # Make this behave like a fancier ListView
        self.setRootIsDecorated(False)
        self.setExpandsOnDoubleClick(False)
        
        self.expanded.connect(lambda index: self.collapse(index))





class ColumnView(QtGui.QColumnView):
    
    def __init__(self):
        super(ColumnView, self).__init__()
        self.setMinimumWidth(800)
        self.setColumnWidths([200, 150, 150, 120, 400] + [150] * 20)
    
    def createColumn(self, index):
        
        node = self.model().node_from_index(index)
        header = node.label or 'NO LABEL'

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
obj.setModel(model)

obj.show()
obj.raise_()

exit(app.exec_())
