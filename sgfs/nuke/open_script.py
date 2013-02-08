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
from sgfs.ui.picker.nodes.sgfs import TemplateGlobPicker


class Dialog(QtGui.QDialog):
    
    def __init__(self, *args, **kwargs):
        super(Dialog, self).__init__(*args, **kwargs)
        self._setupGui()

    def _setupGui(self):

        self.setWindowTitle('Open Script from Work Area')
        self.setLayout(QtGui.QVBoxLayout())

        self._pickerModel, self._pickerView = any_task(
            path=nuke.root().name(),
            extra_node_types=[functools.partial(
                TemplateGlobPicker,
                    entity_types=['Task'],
                    template='nuke_scripts_dir',
                    glob='*.nk',
                ),
            ],
        )

        self._pickerView.setFixedSize(600, 250)
        self._pickerView.setPreviewVisible(False)
        self._pickerView.nodeChanged.connect(self._pickerNodeChanged)

        self.layout().addWidget(self._pickerView)
        
        self._button = button = QtGui.QPushButton('Open', clicked=self._onOpenClicked)

        self.layout().addWidget(button)

        self._pickerNodeChanged(self._pickerView.currentNode())
    
    def show(self):
        super(Dialog, self).show()
        self.setMinimumSize(self.size())
        self.setMaximumHeight(self.height())
    
    def _pickerNodeChanged(self, node):
        self._button.setEnabled(
            'path' in node.state
        )

    def _onOpenClicked(self, *args):
        path = self._pickerView.currentNode().state.get('path')
        if path:
            nuke.scriptOpen(path)
        self.close()


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

