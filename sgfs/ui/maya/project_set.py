import os

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds, mel

from sgfs.ui.picker import presets as picker_presets


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Select Workspace")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.setLayout(QtGui.QVBoxLayout())
        
        workspace = cmds.workspace(q=True, rootDirectory=True)
        self._model, self._picker = picker_presets.any_task(path=workspace)
        self._picker.setMaximumHeight(400)
        self._picker.setPreviewVisible(False)
        self._picker.nodeChanged = self._on_node_changed
        self.layout().addWidget(self._picker)
        
        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch()
        self.layout().addLayout(button_layout)
        self._button = QtGui.QPushButton("Set Project")
        self._button.setEnabled(False)
        self._button.clicked.connect(self._on_set_project)
        button_layout.addWidget(self._button)
        
        # Trigger a button update.
        self._on_node_changed(self._picker.currentNode())
    
    def _on_node_changed(self, node):
        self._node = node
        self._enable = 'Task' in node.state
        if self._enable:
            self._path = self._model.sgfs.path_for_entity(node.state['Task'])
            self._enable = self._path is not None and os.path.exists(os.path.join(self._path, 'maya', 'workspace.mel'))
        self._button.setEnabled(self._enable)
        
    def _on_set_project(self):
        workspace = os.path.join(self._path, 'maya')

        # We *really* set the workspace.
        os.chdir(workspace)
        cmds.workspace(workspace, openWorkspace=True)
        cmds.workspace(dir=workspace)
        mel.eval('addRecentProject("%s");' % workspace)
        
        print '# Workspace set to:', workspace

        self.hide()


def __before_reload__():
    if dialog:
        dialog.close()

dialog = None

def run():
    
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = Dialog()    
    dialog.show()
    dialog.raise_()

