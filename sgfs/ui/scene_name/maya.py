"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

from __future__ import absolute_import

import os
import platform

import maya.cmds as cmds
import maya.mel as mm

from .widget import Dialog


dialog = None


def __before_reload__():

    print '__before_reload__'
    
    if dialog:
        dialog.close()


__also_reload__ = ['.widget', '.core']


class MayaDialog(Dialog):
    
    def __init__(self, parent=None):
        super(MayaDialog, self).__init__({
            'workspace': cmds.workspace(q=True, rootDirectory=True) or None,
            'filename': cmds.file(q=True, sceneName=True) or None,
            'warning': self._warning,
            'error': self._error,
            'extension': '.mb',
        }, parent)
    
    def _warning(self, message):
        cmds.warning(message)

    def _error(self, message):
        cmds.confirmDialog(title='Scene Name Error', message=message, icon='critical')
        cmds.error(message)
    
    def _check_overwrite_safety(self, path):
        
        # Good to go if it doesn't exist.
        basic = super(MayaDialog, self)._check_overwrite_safety(path)
        if basic:
            return True
        
        # Ask the user.
        kwargs = dict(
            icon='warning',
            button=['Yes', 'No'],
            cancelButton='No',
            defaultButton='No',
        )
        message = "%s already exists.\nDo you want to replace it?" % os.path.basename(path)
        if platform.system() == 'Darwin':
            kwargs['title'] = message
        else:
            kwargs['title'] = 'Save As'
            kwargs['message'] = message
        return cmds.confirmDialog(**kwargs) == 'Yes'
    
    def _save(self, path):
        cmds.file(rename=path)
        cmds.file(save=True, type='mayaBinary')


def run():
    
    # Hold onto a reference so that it doesn't automatically close.
    global dialog
    
    if dialog:
        dialog.close()
    
    dialog = MayaDialog()
    dialog.show()
    