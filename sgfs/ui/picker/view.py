import functools
import threading

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from uitools.headeredlistview import HeaderedListView, HeaderDisplayRole

from sgfs.ui.picker.utils import icon, state_from_entity
from sgfs.ui.picker.nodes import base


class Header(QtGui.QHeaderView):
    
    def __init__(self, node):
        super(Header, self).__init__(Qt.Horizontal)
        self._node = node
        self.setResizeMode(QtGui.QHeaderView.Stretch)
    
    def _text(self):
        if self._node.is_loading:
            header = 'Loading...'
        else:
            header = self._node.view_data.get('header', '')
                
        header += ' (%d)' % len(self._node.children())
        
        if self._node.error_count:
            header = 'Loading Error'

        return header

    def _setupModel(self):
        # We need a horrible hack to get different headers in different columns.
        # Before every paint event we update the data that the model will
        # provide when requested in real painting implementation.
        self.model()._header = self._text()

    def paintEvent(self, e):
        self._setupModel()
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


class OldHeaderedListView(QtGui.QTreeView):
    
    # This needs to be a signal so that it runs in the main thread.
    layoutChanged = QtCore.pyqtSignal()


    def __init__(self, masterView, model, index, node):
        super(HeaderedListView, self).__init__()
        
        self._masterView = masterView
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
        
        self.layoutChanged.connect(self._scrollToCurrentIndex)
        self.layoutChanged.connect(self.resizeToContents)

        # Transfer standard behaviour and our options to the new column.
        self._masterView.initializeColumn(self)

        self._deferResize()


    # We need a hook for resizing columns after the column view has
    # inserted this column; see self._deferResize().
    _columnViewSetUp = QtCore.pyqtSignal([int])

    def _deferResize(self):

        # We need some wacky work-around to be able to set the width of the
        # field, since we can't setColumnWidths while the column is being
        # created, and we don't seem to have any other hooks. So we setup
        # a thread to call our signal in the event loop to  call the proper
        # sizing function.

        # We set the minimum size here (and reset it in the event) so that
        # the animation by QColumnView is still correct.

        # Only bother if we already have a size.
        width = self.sizeHintForColumn(0)
        if width > 0:
            old_min = self.minimumWidth()
            self.setMinimumWidth(width + 32) # 32 -> decoration padding.
            self._columnViewSetUp.connect(self._handleDeferredResize, Qt.QueuedConnection)
            self._columnViewSetUp.emit(old_min)

    def _handleDeferredResize(self, old_min):
        self.setMinimumWidth(old_min)
        self.resizeToContents()

    def __repr__(self):
        return '<HeaderedListView %r at 0x%x>' % (self._node.view_data.get('header'), id(self))
    
    def _scrollToCurrentIndex(self):
        node = self.model().node_from_index(self.selectionModel().currentIndex())
        while node.parent:
            if node.parent is self._node:
                self.scrollTo(node.index)
                return
            node = node.parent

    def resizeToContents(self):
        
        width = self.sizeHintForColumn(0)

        # Don't bother if we can't figure it out.
        if width <= 0:
            return

        # Pad for icons and decorations.
        width += 32
        
        # Determine our depth in the view.
        column = 0
        index = self.rootIndex()
        while index.isValid():
            column += 1
            index = index.parent()

        # Set the width.
        widths = self._masterView.columnWidths()
        if not widths:
            widths = [100]
        while len(widths) <= column + 1:
            widths.append(widths[-1])
        widths[column] = width
        self._masterView.setColumnWidths(widths)



class ColumnView(QtGui.QColumnView):
    
    # Emitted whenever a different node is selected.
    nodeChanged = QtCore.pyqtSignal([object])

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('verticalScrollMode', self.ScrollPerPixel)
        kwargs.setdefault('selectionMode', self.SingleSelection)
        super(ColumnView, self).__init__(*args, **kwargs)
        
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

        view = HeaderedListView()
        view.setModel(self.model())
        view.setRootIndex(index)

        self.initializeColumn(view)
        view.restoreAfterInitialize()

        # view = HeaderedListView(self, self.model(), index, node)
        
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
    
    # TODO: Deprecate.
    def currentState(self):
        return self.currentNode().state
    
    def currentChanged(self, current, previous):
        super(ColumnView, self).currentChanged(current, previous)

        # Ideally I would connect to the same signal on the selectionModel that
        # this object does, but it is easier for me to just overload this slot.
        self.nodeChanged.emit(self.model().node_from_index(current))

    def setEntityFromPath(self, path, entity_types=None):

        entities = self.model().sgfs.entities_from_path(path, entity_types)
        if not entities:
            return False

        init_state = state_from_entity(entities)
        index = self.model().index_from_state(init_state)
        if not index:
            return False

        self.setCurrentIndex(index)
        return True



