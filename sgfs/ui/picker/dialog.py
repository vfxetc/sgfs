import os

from uitools.qt import Q

from . import presets as picker_presets


class TemplatePickerDialog(Q.Widgets.Dialog):
    
    def __init__(self, *args, **kwargs):
        self._templateName = kwargs.pop('templateName')
        kwargs.setdefault('windowTitle', 'Select Task')
        super(TemplatePickerDialog, self).__init__(*args, **kwargs)
        self._setupGui()
    
    def _setupGui(self):

        self.setMinimumWidth(1000)
        self.setMinimumHeight(400)
        
        self.setLayout(Q.VBoxLayout())
        
        self._model, self._picker = self._buildPicker()

        self._picker.setMaximumHeight(400)
        self._picker.setPreviewVisible(False)
        self._picker.nodeChanged.connect(self._onNodeChanged)

        self.layout().addWidget(self._picker)
        
        button_layout = Q.HBoxLayout()
        self.layout().addLayout(button_layout)

        self._cancelButton = Q.PushButton("Cancel")
        self._cancelButton.clicked.connect(self._onCancel)
        button_layout.addWidget(self._cancelButton)

        button_layout.addStretch()

        self._makeButton = Q.PushButton("Make Folder")
        self._makeButton.setEnabled(False)
        self._makeButton.clicked.connect(self._onSelectMakeFolder)
        button_layout.addWidget(self._makeButton)
        
        self._selectButton = Q.PushButton("Select")
        self._selectButton.setEnabled(False)
        self._selectButton.clicked.connect(self._onSelect)
        button_layout.addWidget(self._selectButton)

        # Trigger a button update.
        self._onNodeChanged(self._picker.currentNode())
    
    def _currentWorkspace(self):
        return os.getcwd()

    def _buildPicker(self):
        return picker_presets.any_task(path=self._currentWorkspace())

    def _onNodeChanged(self, node):
        
        self._node = node
        self._enable = False
        self._path = None

        if 'self' in node.state:
            try:
                self._path = self._model.sgfs.path_from_template(node.state['self'], self._templateName)
            except ValueError:
                pass
            else:
                self._enable = os.path.exists(self._path)
        
        self._selectButton.setEnabled(self._enable) 
        self._makeButton.setEnabled(bool(self._path) and not self._enable)
    
    def _onCancel(self):
        self.hide()
    
    def _onSelect(self):
        self.hide()

    def _onSelectMakeFolder(self):
        self._model.sgfs.create_structure(self._node.state['self'])
        self._onNodeChanged(self._node) # Not the best behaviour in the world.
        



