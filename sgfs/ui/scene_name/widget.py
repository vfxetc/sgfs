"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

import os

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from .core import SceneName


class SceneNameWidget(QtGui.QWidget):
        
    def __init__(self, kwargs=None, parent=None):
        super(SceneNameWidget, self).__init__(parent)
        self._setup_namer(kwargs or {})
        self._setup_ui()
    
    @property
    def namer(self):
        return self._namer
    
    def _setup_namer(self, kwargs):
        kwargs.setdefault('workspace', os.getcwd())
        self._namer = SceneName(**kwargs)
        
    def _setup_ui(self):
        
        # Main layouts.
        self._layout = QtGui.QVBoxLayout()
        self.setLayout(self._layout)
        self._form_layout = QtGui.QGridLayout()
        self._layout.addLayout(self._form_layout)
        self._columns = 0
    
        # Entity name.
        edit = self._entity_name_edit = QtGui.QLineEdit()
        edit.setText(self._namer.entity_name)
        edit.textChanged.connect(self.update_preview)
        self._add_form_column('Shot/Asset Name', edit)
        
        # Step name.
        self._step_name_combo = QtGui.QComboBox()
        self._build_step_combo()
        self._step_name_combo.activated.connect(self.update_preview)
        self._add_form_column('Task', self._step_name_combo)
        
        # Description.
        edit = self._detail_edit = QtGui.QLineEdit()
        edit.setText(self._namer.detail)
        edit.textChanged.connect(self.update_preview)
        edit.setFocus()
        self._add_form_column('Detail (optional)', edit)
        
        # Version.
        spinner = self._version_spinner = QtGui.QSpinBox()
        spinner.textFromValue = lambda x: '%04d' % x
        spinner.setValue(self._namer.version)
        spinner.setMinimum(1)
        spinner.setMaximum(9999)
        spinner.valueChanged.connect(self.update_preview)
        self._add_form_column('Version', spinner)
        
        # Revision.
        spinner = self._revision_spinner = QtGui.QSpinBox()
        spinner.textFromValue = lambda x: '%04d' % x
        spinner.setValue(self._namer.revision)
        spinner.setMinimum(0)
        spinner.setMaximum(9999)
        spinner.valueChanged.connect(self.update_preview)
        self._add_form_column('Revision', spinner)
        
        # Name preview.
        label = self._preview_label = QtGui.QLabel()
        label.setAlignment(Qt.AlignHCenter)
        label.setContentsMargins(6, 6, 6, 6)
        self._layout.addWidget(label)
        
        # Prime the preview.
        self.update_preview()
    
    def _build_step_combo(self):
        combo = self._step_name_combo
        combo.clear()
        for i, step in enumerate(self._namer.get_step_names()):
            combo.addItem(step)
            if step == self._namer.step_name:
                combo.setCurrentIndex(i)
            
    def _add_form_column(self, label, widget):
        if label:
            self._form_layout.addWidget(QtGui.QLabel(label), 0, self._columns)
        self._form_layout.addWidget(widget, 1, self._columns)
        self._columns += 1
    
    def namer_updated(self):
        # Need to extract all info first since changing it will trigger update_preview.
        entity_name, detail, version, revision = self._namer.entity_name, self._namer.detail, self._namer.version, self._namer.revision
        self._build_step_combo()
        self._entity_name_edit.setText(entity_name)
        self._detail_edit.setText(detail)
        self._version_spinner.setValue(version)
        self._revision_spinner.setValue(revision)
        
    def update_preview(self, *args):
        """Update the displayed path, and the warning to the user if it exists."""
        
        self._namer.entity_name = str(self._entity_name_edit.text())
        self._namer.step_name = str(self._step_name_combo.currentText())
        self._namer.detail = str(self._detail_edit.text())
        self._namer.version = self._version_spinner.value()
        self._namer.revision = self._revision_spinner.value()        
        path = self._namer.get_path()
        rel_path = os.path.relpath(path, self._namer.workspace)
        self._preview_label.setText('<workspace>/' + rel_path)
        if os.path.exists(path):
            
            # Pick an error color appropriate for the background color.
            palette = QtGui.QApplication.palette()
            bg = palette.color(palette.Window)
            if bg.red() > 127:
                fg = 'darkRed'
            else:
                fg = 'orange' # Red it too bright to read.
                
            self._preview_label.setStyleSheet('QLabel { color: %s; }' % fg)
        
        else:
            self._preview_label.setStyleSheet('')
    
    # For backward compatibility.
    _on_user_action = update_preview
    update_ui = update_preview
    

class Dialog(QtGui.QDialog):
    
    def __init__(self, kwargs=None, parent=None):
        super(Dialog, self).__init__(parent)
        
        self.setWindowTitle('(Re)Name Scene')
        
        # The main widget.
        self._widget = SceneNameWidget(kwargs)
        self.setLayout(self._widget.layout())
        
        # Save button.
        save_button = QtGui.QPushButton('Save')
        save_button.clicked.connect(self._on_save_button)
        self.layout().addWidget(save_button)
    
    def show(self):
        super(Dialog, self).show()
        self.setMinimumSize(self.size())
        self.setMaximumHeight(self.height())
    
    def _check_overwrite_safety(self, path):
        return not os.path.exists(path)
    
    def _save(self, path):
        raise NotImplementedError('Must override!')
    
    def _on_save_button(self, *args):
        path = self._widget._namer.get_path()
        if not self._check_overwrite_safety(path):
            return
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        print 'Save to', repr(path)
        self._save(path)
        self.close()

