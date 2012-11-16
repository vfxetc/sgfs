"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

from __future__ import absolute_import

import os
import re
import difflib
import sys

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from ..sgfs import SGFS


sgfs = SGFS()


def silk(name):
    return os.path.abspath(os.path.join(
        __file__, '..', '..', '..', 'icons', 'silk', name + '.png'
    ))


def silk_icon(name, size=16):
    icon = QtGui.QIcon(silk(name))
    if size != 16:
        icon = QtGui.QIcon(icon.pixmap(size, size))
    return icon


class ComboBox(QtGui.QComboBox):
    
    def __init__(self, *args, **kwargs):
        super(ComboBox, self).__init__(*args, **kwargs)
        self.setCurrentIndex(0)
        
    def itemData(self, index):
        data = super(ComboBox, self).itemData(index).toPyObject()
        return self._conform_item_data(data)
    
    def _conform_item_data(self, data):
        if isinstance(data, QtCore.QString):
            return str(data)
        if isinstance(data, dict):
            return dict((self._conform_item_data(k), self._conform_item_data(v)) for k, v in data.iteritems())
        return data
    
    def currentData(self):
        index = self.currentIndex()
        return self.itemData(index)
    
    def indexWithData(self, data):
        for i in xrange(self.count()):
            if self.itemData(i) == data:
                return i
    
    def selectWithData(self, data):
        index = self.indexWithData(data)
        if index is not None:
            self.setCurrentIndex(index)
            return True
    
    def iterData(self):
        for i in xrange(self.count()):
            yield self.itemData(i)


class Labeled(QtGui.QVBoxLayout):

    def __init__(self, label, widget):
        super(Labeled, self).__init__()
        self._label = QtGui.QLabel(label)
        self.addWidget(self._label)
        self._widget = widget
        self.addWidget(widget)
    
    def setVisible(self, visible):
        self._label.setVisible(visible)
        self._widget.setVisible(visible)


class Section(QtGui.QVBoxLayout):

    def __init__(self, parent, widget, index, name, iter_func):
        super(Section, self).__init__()
        
        self._widget = widget
        self._index = index
        
        self._name = name
        self._iter_func = iter_func
        
        self._label = QtGui.QLabel(name, parent=parent)
        self.addWidget(self._label)
        
        self._combobox = ComboBox(parent=parent)
        self._combobox.activated.connect(self._on_activated)
        self.addWidget(self._combobox)
    
    def repopulate(self, path):
        self._combobox.clear()
        
        items = list(self._iter_func(path))
        if not self._index:
            items.append(('Custom', _custom_sentinel, None))
        selected = max(items, key=lambda item: item[2]) if items else None
        
        for i, item in enumerate(items):
            name, path, priority = item
            self._combobox.addItem(name, path)
            if item is selected:
                self._combobox.setCurrentIndex(i)
        
        # Trigger the next box to populate.
        self._on_activated(self._combobox.currentIndex())
        
    def _on_activated(self, index):
        path = self._combobox.itemData(index)
        self._widget._on_section_changed(self._index, path)
    
    def setVisible(self, visible):
        self._label.setVisible(visible)
        self._combobox.setVisible(visible)


_custom_sentinel = object()


class Layout(QtGui.QHBoxLayout):
    
    def __init__(self, parent=None, browse_name='Product', browse_filter=''):
        super(Layout, self).__init__()
        
        self._browse_name = browse_name
        self._browse_filter = browse_filter
        
        self._parent = parent
        
        self._sections = []
        self._setup_sections()
        
        self._setup_ui()
    
    def _setup_sections(self):
        self.register_section("Entity", self._iter_entity_items)
        self.register_section("Step", self._iter_step_items)
    
    def register_section(self, name, iter_func):
        self._sections.append(Section(
            self._parent,
            self,
            len(self._sections),
            name,
            iter_func,
        ))
    
    def _setup_ui(self):
        
        self._pairs = []
        
        for section in self._sections:
            self.addLayout(section)
        
        self._custom_field = QtGui.QLineEdit(parent=self._parent)
        self._custom_field.editingFinished.connect(self._on_custom_edited)
        self._custom_pair = Labeled("Custom Path", self._custom_field)
        self.addLayout(self._custom_pair)
        
        self._browse_button = QtGui.QPushButton(silk_icon('folder', 12), "Browse", parent=self._parent)
        self._browse_button.setMaximumSize(QtCore.QSize(75, 20))
        self._browse_button.clicked.connect(self._on_browse)
        self._browse_pair = Labeled("", self._browse_button)
        self.addLayout(self._browse_pair)
        
        self._sections[0].repopulate(self.root())
    
    def root(self):
        return cmds.workspace(q=True, rootDirectory=True)
    
    def _on_section_changed(self, section_index, path):
        
        is_custom = path is _custom_sentinel
        
        # Handle visiblity.
        self._custom_pair.setVisible(is_custom)
        self._browse_pair.setVisible(is_custom)
        for i, section in enumerate(self._sections):
            section.setVisible(i <= section_index or not is_custom)
        
        # Populate the next in the chain.
        if is_custom:
            self.path_changed(self.path())
        else:
            if section_index + 1 < len(self._sections):
                self._sections[section_index + 1].repopulate(path)
            else:
                full_path = self.path()
                self.path_changed(full_path)
                if full_path is not None:
                    self._custom_field.setText(full_path)
    
    def _on_custom_edited(self):
        self.path_changed(self.path())
    
    def _iter_entity_items(self, workspace):
            
        tasks = sgfs.entities_from_path(workspace)
        if not tasks or tasks[0]['type'] != 'Task':
            cmds.warning('Workspace does not have any tasks; %r -> %r' % (workspace, tasks))
            return
        
        task = tasks[0]
        entity = task.parent()
        entities = []
        
        # Populate shot combo with all reuses that match the current workspace.
        if entity['type'] == 'Shot':
            seq = entity.parent()
            seq_path = sgfs.path_for_entity(seq)
            for shot_path, shot in sgfs.entities_in_directory(seq_path, "Shot", load_tags=None):
                if shot.fetch('code').startswith(entity.fetch('code')[:6]):
                    entities.append((
                        shot['code'], shot_path
                    ))
        
        elif entity['type'] == 'Asset':
            entities.append((
                entity.fetch('code'), sgfs.path_for_entity(entity)
            ))
        
        else:
            cmds.warning('Cannot extract entities from %r' % entity)
        
        for i, (name, path) in enumerate(entities):
            yield name, path, 1
    
    def _iter_step_items(self, entity_path):
        if not entity_path:
            return
        
        step_codes = set()
        for path, task in sgfs.entities_in_directory(entity_path, 'Task', load_tags=None):
            
            # Some of our tags are missing parts and I'm not sure why.
            if 'step' not in task:
                cmds.warning('%r does not have a cached step' % task)
                
            # Only add one of every step.
            step_code = task.fetch('step').fetch('code')
            if step_code in step_codes:
                continue
            step_codes.add(step_code)
            
            yield step_code, path, 1 if step_code.lower().startswith('anim') else 0
    
    def _browse(self):
        return str(QtGui.QFileDialog.getOpenFileName(self.parentWidget(), "Select %s" % self._browse_name, self.root(), self._browse_filter))
        
    def _on_browse(self):
        path = self._browse()
        if not path:
            return
        self._set_custom(path)
    
    def _set_custom(self, file_name):
        root = self.root()
        relative = os.path.relpath(file_name, root)
        if relative.startswith('.'):
            self._custom_field.setText(file_name)
        else:
            self._custom_field.setText(relative)
        self.path_changed(self.path())
    
    def path(self):
        
        workspace = cmds.workspace(q=True, directory=True)
        
        path_parts = [self.root()]
        for section in self._sections:
            path = section._combobox.currentData()
            if path is _custom_sentinel:
                return str(self._custom_field.text())
            if path is None:
                return
            path_parts.append(path)
        
        return os.path.join(*path_parts)
    
    def path_changed(self, path):
        pass

    def setPath(self, full_path):
        
        # Try to match it.
        matches = []
        for section_i, section in enumerate(self._sections):
            section.repopulate(matches[-1] if matches else self.root())
            for path in section._combobox.iterData():
                if path is _custom_sentinel:
                    continue
                if full_path == path or full_path.startswith(path + '/'):
                    matches.append(path)
                    break
            else:
                # Could not find it.
                self._sections[0]._combobox.selectWithData(_custom_sentinel)
                self._on_section_changed(0, _custom_sentinel)
                self._set_custom(full_path)
                return
        
        for i, path in enumerate(matches):
            self._sections[i]._combobox.selectWithData(path)

