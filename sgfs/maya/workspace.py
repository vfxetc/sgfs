"""

Workspaces and Projects
=======================

.. note:: I have waffled back and forth about if these sorts of tools should be
    named "workspace" or "project", but I'm going to put my foot down and say
    "workspace", since that is the name of the command that you use to modify
    it.

"""

import os
import sys
from subprocess import call

from maya import cmds, mel

from sgfs import SGFS
from sgfs.ui.picker.dialog import TemplatePickerDialog


def workspace_path(workspace=None):

    # Getter.
    if workspace is None:
        # TODO: get entities via memory, or scene info, and then finally take it
        # from the workspace. Prompt the user if there is more than one.
        return cmds.workspace(q=True, rootDirectory=True) or os.path.join(os.getcwd(), 'maya')

    # Setter: we try really hard to set the workspace.
    os.chdir(workspace)
    cmds.workspace(workspace, openWorkspace=True)
    cmds.workspace(dir=workspace)
    mel.eval('addRecentProject("%s");' % workspace)
    
    print '# Workspace set to:', workspace


class WorkspacePickerDialog(TemplatePickerDialog):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('templateName', 'maya_workspace')
        super(WorkspacePickerDialog, self).__init__(*args, **kwargs)

    def _setupGui(self):
        super(WorkspacePickerDialog, self)._setupGui()

        # This is what the Maya artists are used to. Feel free to remove this
        # between shows.
        self._picker.setColumnWidths([198] + [200] * 10)

    def _currentWorkspace(self):
        return workspace_path()
    
    def _onSelect(self):
        workspace_path(self._path)
        super(WorkspacePickerDialog, self)._onSelect()


_pick_and_set_workspace_dialog = None

def __before_reload__():
    if _pick_and_set_workspace_dialog:
        _pick_and_set_workspace_dialog.close()


def open_workspace():

    path = workspace_path()
    
    sgfs = SGFS()
    entities = sgfs.entities_from_path(workspace_path(), ['Task', 'PublishEvent'])
    if entities:
        path = sgfs.path_for_entity(entities[0]) or path

    if sys.platform == 'darwin':
        call(['open', path])
    else:
        call(['xdg-open', path])


def pick_workspace():
    """Shelf tool to open task-picking dialog to set the workspace."""

    global _pick_and_set_workspace_dialog
    
    if _pick_and_set_workspace_dialog:
        _pick_and_set_workspace_dialog.close()
    
    _pick_and_set_workspace_dialog = dialog = WorkspacePickerDialog()    
    dialog.show()
    dialog.raise_()


def assert_workspace():

    scene_path = cmds.file(q=True, sceneName=True)
    if not scene_path:
        raise ValueError("Scene is not saved.")

    sgfs = SGFS()
    tasks = sgfs.entities_from_path(scene_path, ['Task'])
    if not tasks:
        raise ValueError("Scene is not in a task.")

    path = sgfs.path_for_entity(tasks[0])
    workspace_path(path)


def open_parent_in_shotgun():
    """Shelf tool to open Asset or Shot for current workspace."""

    entities = SGFS().entities_from_path(workspace_path(), ['Asset', 'Shot'])
    if not entities:
        cmds.error('No entities for workspace.')
        return

    if sys.platform == 'darwin':
        call(['open', entities[0].url])
    else:
        call(['xdg-open', entities[0].url])
