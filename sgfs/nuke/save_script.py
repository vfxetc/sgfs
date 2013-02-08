"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

from __future__ import absolute_import

import functools
import os

import nuke

from uitools.qt import QtGui
from sgfs.ui.scene_name.widget import SceneNameWidget
from sgfs.ui.picker.presets import any_task
from sgfs.ui.picker.nodes.sgfs import DirectoryPicker


class Dialog(QtGui.QDialog):
    
    def __init__(self, kwargs=None, parent=None):
        super(Dialog, self).__init__(parent)

        filename = nuke.root().name()
        if filename == 'Root':
            filename = ''

        self._kwargs = {
            'workspace': os.path.dirname(nuke.root().name()),
            'filename': filename,
            'directory': '',
            'warning': nuke.warning,
            'error': nuke.error,
            'extension': '.nk',
        }
        self._kwargs.update(kwargs or {})
        self._setupGui()

    def _setupGui(self):

        self.setWindowTitle('Save Script to Work Area')
        self.setLayout(QtGui.QVBoxLayout())

        self._pickerModel, self._pickerView = any_task(
            path=os.path.dirname(nuke.root().name()),
            extra_node_types=[functools.partial(
                DirectoryPicker,
                entity_types=['Task'],
                template='nuke_scripts_dir',
                ),
            ],
        )

        self._pickerView.setFixedSize(600, 250)
        self._pickerView.setPreviewVisible(False)
        self._pickerView.nodeChanged.connect(self._pickerNodeChanged)

        self.layout().addWidget(self._pickerView)

        # The main widget.
        self._sceneName = SceneNameWidget(self._kwargs)
        self.layout().addWidget(self._sceneName)
        
        # Save button.
        self._button = button = QtGui.QPushButton('Save', clicked=self._onSaveClicked)

        self.layout().addWidget(button)

        self._pickerNodeChanged(self._pickerView.currentNode())
    
    def show(self):
        super(Dialog, self).show()
        self.setMinimumSize(self.size())
        self.setMaximumHeight(self.height())
    
    def _pickerNodeChanged(self, node):

        entity = node.state.get('Shot') or node.state.get('Asset')
        if entity:
            self._sceneName.setEntityName(entity.get('code') or entity.get('name'))

        if 'path' in node.state:
            self._sceneName.setWorkspace(node.state['workspace'])
            relpath = os.path.relpath(node.state['path'], node.state['workspace'])
            self._sceneName.setDirectory(relpath)


        self._button.setEnabled(
            'path' in node.state
        )

    def _onSaveClicked(self, *args):
        path = os.path.join(
            self._pickerView.currentNode().state['path'],
            self._sceneName._namer.get_basename(),
        )
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

