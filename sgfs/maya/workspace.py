"""

Workspaces and Projects
=======================

.. note:: I have waffled back and forth about if these sorts of tools should be
    named "workspace" or "project", but I'm going to put my foot down and say
    "workspace", since that is the name of the command that you use to modify
    it.

"""

import sys
from subprocess import call

from maya import cmds

from sgfs import SGFS


def open_parent_in_shotgun():
    """Shelf tool to open Asset or Shot for current workspace."""

    # TODO: get entities via memory, or scene info, and then finally take it
    # from the workspace. Prompt the user if there is more than one.

    workspace = cmds.workspace(q=True, rootDirectory=True)
    if not workspace:
        cmds.error('Workspace not set.')
        return

    entities = SGFS().entities_from_path(workspace, ['Asset', 'Shot'])
    if not entities:
        cmds.error('No entities for workspace.')
        return

    if sys.platform == 'darwin':
        call(['open', entities[0].url])
    else:
        call(['xdg-open', entities[0].url])
