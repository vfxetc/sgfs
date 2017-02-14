import os

from uitools.qt import QtGui

from . import presets as picker_presets


class TemplatePickerDialog(QtGui.QDialog):
    
    def __init__(self, *args, **kwargs):
        self._templateName = kwargs.pop('templateName')
        kwargs.setdefault('windowTitle', 'Select Task')
        super(TemplatePickerDialog, self).__init__(*args, **kwargs)
        self._setupGui()
    
    def _setupGui(self):

        self.setMinimumWidth(1000)
        self.setMinimumHeight(400)
        
        self.setLayout(QtGui.QVBoxLayout())
        
        self._model, self._picker = self._buildPicker()

        self._picker.setMaximumHeight(400)
        self._picker.setPreviewVisible(False)
        self._picker.nodeChanged.connect(self._onNodeChanged)

        self.layout().addWidget(self._picker)
        
        button_layout = QtGui.QHBoxLayout()
        self.layout().addLayout(button_layout)

        self._cancelButton = QtGui.QPushButton("Cancel")
        self._cancelButton.clicked.connect(self._onCancel)
        button_layout.addWidget(self._cancelButton)

        button_layout.addStretch()

        self._button = QtGui.QPushButton("Select")
        self._button.setEnabled(False)
        self._button.clicked.connect(self._onSelect)
        button_layout.addWidget(self._button)

        self._makeButton = QtGui.QPushButton("Make Folder")
        self._makeButton.setEnabled(False)
        self._makeButton.clicked.connect(self._onSelectMakeFolder)
        button_layout.addWidget(self._makeButton)
        
        # Trigger a button update.
        self._onNodeChanged(self._picker.currentNode())
    
    def _currentWorkspace(self):
        return os.getcwd()

    def _buildPicker(self):
        return picker_presets.any_task(path=self._currentWorkspace())

    def _onNodeChanged(self, node):
        
        self._node = node
        self._enable = False
        if 'self' in node.state:
            try:
                self._path = self._model.sgfs.path_from_template(node.state['self'], self._templateName)
            except ValueError:
                self._makeButton.setEnabled(True)
                pass
            else:
                self._enable = os.path.exists(self._path)
        self._button.setEnabled(self._enable)

    
    def _onCancel(self):
        self.hide()
    
    def _onSelect(self):
        self.hide()

    def _onSelectMakeFolder(self):
        self._model.sgfs.create_structure(self._node.state['self'])
        
        print "os path exists", os.path.exists(self._path)
        self.hide()
        



