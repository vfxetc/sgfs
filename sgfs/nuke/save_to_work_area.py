"""

This is lifted directoy out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

"""

from __future__ import absolute_import

import os
import platform

import nuke

from sgfs.ui.scene_name.widget import Dialog


class NukeDialog(Dialog):
    
    def __init__(self, parent=None):
        super(NukeDialog, self).__init__({
            'workspace': nuke.root().name(),
            'filename': nuke.root().name(),
            'directory': 'scripts/comp',
            'warning': nuke.warning,
            'error': nuke.error,
            'extension': '.nk',
        }, parent)
    
    def _check_overwrite_safety(self, path):
        
        # Good to go if it doesn't exist.
        basic = super(NukeDialog, self)._check_overwrite_safety(path)
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
        
        # return cmds.confirmDialog(**kwargs) == 'Yes'
    
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
    
    dialog = NukeDialog()
    dialog.show()

