"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

from __future__ import absolute_import

import os
import platform

import nuke

from uitools.qt import QtGui
from sgfs.ui.scene_name.widget import SceneNameWidget
from sgfs.ui.picker.presets import any_task


class Dialog(QtGui.QDialog):
    
    def __init__(self, kwargs=None, parent=None):
        super(Dialog, self).__init__(parent)

        self._kwargs = {
            'workspace': os.path.dirname(nuke.root().name()),
            'filename': nuke.root().name(),
            'directory': 'scripts/comp',
            'warning': nuke.warning,
            'error': nuke.error,
            'extension': '.nk',
        }
        self._kwargs.update(kwargs or {})
        self._setupGui()

    def _setupGui(self):

        self.setWindowTitle('Save Script to Work Area')
        self.setLayout(QtGui.QVBoxLayout())

        self._pickerModel, self._pickerView = any_task(path=nuke.root().name())
        self._pickerView.setFixedSize(600, 250)
        self._pickerView.setPreviewVisible(False)
        self.layout().addWidget(self._pickerView)

        # The main widget.
        self._sceneName = SceneNameWidget(self._kwargs)
        self.layout().addWidget(self._sceneName)
        
        # Save button.
        button = QtGui.QPushButton('Save', clicked=self._onSaveClicked)
        self.layout().addWidget(button)
    
    def show(self):
        super(Dialog, self).show()
        self.setMinimumSize(self.size())
        self.setMaximumHeight(self.height())
    
    def _onSaveClicked(self, *args):
        path = self._sceneName.path()
        if not self._checkOverwriteSafety(path):
            return
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        print 'Save to', repr(path)
        self._save(path)
        self.close()
    
    def _checkOverwriteSafety(self, path):
        
        basic = not os.path.exists(path)
        if basic:
            return True

        message = "%s already exists.\nDo you want to replace it?" % os.path.basename(path)
        return nuke.ask(message)
    
    def _save(self, path):
        nuke.scriptSaveAs(path, 1)


dialog = None

def __before_reload__():    
    if dialog:
        dialog.close()

def run():
    
    # Hold onto a reference so that it doesn't automatically close.
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = Dialog()
    dialog.show()

