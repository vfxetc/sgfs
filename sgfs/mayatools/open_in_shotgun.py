import sys
from subprocess import call

from maya import cmds

from sgfs import SGFS


def run():
    
    workspace = cmds.workspace(q=True, rootDirectory=True)
    if not workspace:
        cmds.error('Workspace not set.')
        return

    entities = SGFS().entities_from_path(workspace, ('Asset', 'Shot'))
    if not entities:
        cmds.error('No entities for workspace.')
        return

    if sys.platform == 'darwin':
        call(['open', entities[0].url])
    else:
        call(['xdg-open', entities[0].url])
