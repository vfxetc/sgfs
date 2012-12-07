import functools
import pprint

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs.ui.picker.utils import debug, icon
from sgfs.ui.picker.nodes import base


class Header(QtGui.QHeaderView):
    
    def __init__(self, node):
        super(Header, self).__init__(Qt.Horizontal)
        self._node = node
        self.setResizeMode(QtGui.QHeaderView.Stretch)
        
    def paintEvent(self, e):
            
        # We need a horrible hack to get different headers in different columns.
        # Before every paint event we update the data that the model will
        # provide when requested in real painting implementation.
        
        if self._node.is_loading:
            header = 'Loading...'
        else:
            header = self._node.view_data.get('header', '')
                
        header += ' (%d)' % len(self._node.children())
        
        if self._node.error_count:
            header = 'Loading Error'
        
        self.model()._header = header
        
        super(Header, self).paintEvent(e)


class HeaderedListViewDelegate(QtGui.QStyledItemDelegate):
    
    def sizeHint(self, *args):
        size = super(HeaderedListViewDelegate, self).sizeHint(*args)
        return size.expandedTo(QtCore.QSize(1, 20))
    
    def paint(self, painter, options, index):
        
        style = QtGui.QApplication.style()
        style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewRow, options, painter)
        
        # Shift it left by 2 for padding the icons.
        options.rect.adjust(2, 0, 0, 0)
        
        super(HeaderedListViewDelegate, self).paint(painter, options, index)
        
        # Triangle.
        if options.state & QtGui.QStyle.State_Children:
            options.rect.setLeft(options.rect.right() - 12)
            style.drawPrimitive(QtGui.QStyle.PE_IndicatorColumnViewArrow, options, painter)


class HeaderedListView(QtGui.QTreeView):
    
    # This needs to be a signal so that it runs in the main thread.
    layoutChanged = QtCore.pyqtSignal()
    
    def __init__(self, model, index, node):
        super(HeaderedListView, self).__init__()
        
        self._node = node
        
        # Take control over what is displayed in the header.
        self._header = Header(node)
        self.setHeader(self._header)
        
        # Make this behave like a fancier QListView. This also allows for the
        # right arrow to select.
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        
        # To force a row height, otherwise it snaps smaller when the
        # "layoutChanged" signal fires.
        self._delegate = HeaderedListViewDelegate()
        self.setItemDelegateForColumn(0, self._delegate)
        
        self.setModel(model)
        self.setRootIndex(index)
        
        self.layoutChanged.connect(self.fix_scroll_for_selection)
    
    def __repr__(self):
        return '<HeaderedListView %r at 0x%x>' % (self._node.view_data.get('header'), id(self))
    
    def fix_scroll_for_selection(self):
        node = self.model().node_from_index(self.selectionModel().currentIndex())
        while node.parent:
            if node.parent is self._node:
                self.scrollTo(node.index)
                return
            node = node.parent


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
        
        view.setContextMenuPolicy(Qt.CustomContextMenu)
        view.customContextMenuRequested.connect(functools.partial(self._on_context_menu, view))
        
        # We must hold a reference to this somewhere so that it isn't
        # garbage collected on us.
        node.view = view
                
        return view
    
    def _on_context_menu(self, view, point):
        index = view.indexAt(point)
        node = self.model().node_from_index(index)
        
        menu = QtGui.QMenu()
        if node.parent and not isinstance(node, base.Group):
            node.parent.add_child_menu_actions(node, menu)
        
        if not menu.isEmpty():
            menu.addSeparator()
        
        menu.addAction(icon('fatcow/arrow_refresh', as_icon=True), "Reload", functools.partial(self._reload_node, node))
        menu.exec_(view.mapToGlobal(point))
        
    def _reload_node(self, node):
        node.reset()
        self.model().dataChanged.emit(node.index, node.index)
        
    def currentNode(self):
        return self.model().node_from_index(self.selectionModel().currentIndex())
    
    def currentState(self):
        return self.currentNode().state
    
    def currentChanged(self, current, previous):
        super(ColumnView, self).currentChanged(current, previous)
        self.nodeChanged(self.currentNode())

    def nodeChanged(self, node):
        self.stateChanged(node.state)
    
    def stateChanged(self, state):
        pass
        # debug('stateChanged:\n%s\n', pprint.pformat(state))
        