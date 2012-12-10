import functools

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs.ui.picker.utils import debug


class ComboBox(QtGui.QComboBox):
    
    def itemData(self, *args):
        return self._clean_data(super(ComboBox, self).itemData(*args).toPyObject())
    
    def currentData(self):
        return self.itemData(self.currentIndex())
    
    def _clean_data(self, data):
        if isinstance(data, dict):
            return dict(self._clean_data(x) for x in data.iteritems())
        if isinstance(data, (tuple, list)):
            return type(data)(self._clean_data(x) for x in data)
        if isinstance(data, QtCore.QString):
            return unicode(data)
        return data


class ComboBoxView(QtGui.QAbstractItemView):
    
    def __init__(self, *args):
        super(ComboBoxView, self).__init__(*args)
        self._boxes = []
        self._setup_ui()
        self._setup_callbacks()
    
    def _setup_ui(self):
        self._viewport = QtGui.QWidget()
        self.setViewport(self._viewport)
        self._layout = QtGui.QHBoxLayout()
        self._viewport.setLayout(self._layout)
        
        self.setFrameShape(QtGui.QFrame.NoFrame)
        
        self.setContentsMargins(0, 0, 0, 0)
        self.setViewportMargins(0, 0, 0, 0)
        self._viewport.setContentsMargins(0, 0, 0, 0)
        self._layout.setContentsMargins(0, 0, 0, 0)
    
    def _setup_callbacks(self):
        for attr in ('currentChanged', 'dataChanged', 'rowsInserted'):
            setattr(self, attr, functools.partial(self._passthrough, attr))
    
    def _passthrough(self, attr, *args):
        debug('passthrough %s', attr)
        getattr(super(ComboBoxView, self), attr)(*args)
        self._setup_boxes()
    
    def setModel(self, model):
        super(ComboBoxView, self).setModel(model)
        model.layoutChanged.connect(self.layoutChanged)
        self._setup_boxes()
    
    def layoutChanged(self):
        debug('layoutChanged')
        self._setup_boxes()
    
    def _setup_boxes(self):
        debug('setup_boxes')
        
        boxes = self._boxes
        
        
        nodes = [self.currentNode()]
        while nodes[0].parent:
            nodes.insert(0, nodes[0].parent)
        non_leaf_nodes = len(nodes) - int(nodes[-1].is_leaf())
        
        # Make sure we have just enough comboboxes.
        while len(boxes) > non_leaf_nodes:
            box = boxes.pop(-1)
            box.hide()
            box.destroy()
            
        while non_leaf_nodes > len(boxes):
            box = ComboBox()
            box.activated.connect(functools.partial(self._box_activated, len(boxes)))
            boxes.append(box)
            self._layout.addWidget(box)
        
        debug('nodes: %r', nodes)
        debug('boxes: %r', boxes)
        
        # Reset them all...
        for node_i, (node, box) in enumerate(zip(nodes, boxes)):
            box.clear()
            children = node.children()
            if node_i + 1 == len(nodes):
                box.addItem('Select...')
            for row, child in enumerate(node.children()):
                
                icon = self.model().data(child.index, Qt.DecorationRole)
                if isinstance(icon, QtGui.QPixmap):
                    icon = QtGui.QIcon(icon)
                if isinstance(icon, QtGui.QIcon):
                    box.addItem(icon, child.view_data[Qt.DisplayRole], child)
                else:
                    box.addItem(child.view_data[Qt.DisplayRole], child)
                
                if node_i + 1 < len(nodes) and child is nodes[node_i + 1]:
                    box.setCurrentIndex(row)
    
    def _box_activated(self, box_i, row_i):
        debug('box_activated(%r, %r)', box_i, row_i)
        box = self._boxes[box_i]
        node = box.itemData(row_i)
        self.setCurrentIndex(node.index)
    
    
    
    def currentNode(self):
        return self.model().node_from_index(self.selectionModel().currentIndex())
    
    def verticalOffset(self):
        return 0
    
    def horizontalOffset(self):
        return 0
    
    def moveCursor(self, action, modifiers):
        #debug('moveCursor(%r, %r)', action, modifiers)
        return self.model().index(0, 0, QtCore.QModelIndex())
    
    def setColumnWidths(self, *args):
        pass

