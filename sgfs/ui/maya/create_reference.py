import functools

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from maya import cmds

from ..picker import presets as picker_presets

__also_reload__ = [
    '..picker.presets',
]


class Dialog(QtGui.QDialog):
    
    def __init__(self):
        super(Dialog, self).__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Create Reference")
        
        self.setLayout(QtGui.QVBoxLayout())
        
        workspace = cmds.workspace(q=True, rootDirectory=True)
        self._model, self._picker = picker_presets.publishes_from_path(workspace)
        self._picker.setMaximumHeight(400)
        self.layout().addWidget(self._picker)
    
    
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
    
