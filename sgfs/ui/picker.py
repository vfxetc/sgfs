# import gevent.monkey
# gevent.monkey.patch_socket()

import sys

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
    'Shot': '{code}',
    'Task': '{step[short_name]} - {content}',
    'PublishEvent': '{code} ({sg_type}) at {sg_version}',
}


class Model(QtCore.QAbstractItemModel):
    
    _header = 'Default'
    
    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QtCore.QVariant()
        return self._header
    
    def setHeaderData(self, section, orientation, data, role):
        if role == Qt.DisplayRole:
            self._header = data
        
    def hasChildren(self, parent):
        return True
    
    def rowCount(self, parent):
        
        # Top-level.
        if not parent.isValid():
            return len(sgfs.project_roots)
        
        entity = parent.internalPointer()
        backref_key = heirarchy[entity['type']]
        if not hasattr(entity, '_model_loaded'):
            # print 'fetching backrefs for', entity, 'on', backref_key
            entity.fetch_backrefs(*backref_key)
            # print entity.backrefs
            entity._model_loaded = True
        return len(entity.backrefs.get(backref_key) or ())
    
    def columnCount(self, parent):
        return 1
    
    def index(self, row, col, parent):
        
        if not parent.isValid():
            entity = sorted(sgfs.project_roots.iterkeys())[row]
            entity._model_parent = parent
            return self.createIndex(row, col, entity)
        
        entity = parent.internalPointer()
        backref_key = heirarchy[entity['type']]
        child = sorted(entity.backrefs.get(backref_key) or ())[row]
        child._model_parent = parent
        return self.createIndex(row, col, child)
    
    def parent(self, child):
        if not child.isValid():
            return QtCore.QModelIndex()
        entity = child.internalPointer()
        return entity._model_parent
    
    def data(self, index, role):
        
        if not index.isValid():
            return QtCore.QVariant()
        
        if role == Qt.DisplayRole:
            entity = index.internalPointer()
            try:
                return entity_name[entity['type']].format(**entity)
            except KeyError as e:
                print e
                return repr(entity)
        
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





class ColumnView(QtGui.QColumnView):
    
    def __init__(self):
        super(ColumnView, self).__init__()
        self.setMinimumWidth(800)
        self.setColumnWidths([200, 100, 120, 400] + [150] * 20)
    
    def createColumn(self, index):
        
        if index.isValid():
            entity = index.internalPointer()
            next_type = heirarchy.get(entity['type'])
            header = next_type[0] if next_type else 'END'
        else:
            header = 'Project'
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
