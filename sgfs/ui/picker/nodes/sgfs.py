from __future__ import absolute_import

import functools

from PyQt4 import QtCore
Qt = QtCore.Qt

from sgfs.ui.picker.utils import icon, call_open
from sgfs.ui.picker.nodes.base import Node


class SGFSRoots(Node):
    
    def update(self, *args):
        super(SGFSRoots, self).update(*args)
        self.view_data.setdefault('header', 'SGFS Project')
        
    @staticmethod
    def is_next_node(state):
        return not state
    
    def child_matches_initial_state(self, child, init_state):
        return 'Project' in init_state and init_state['Project'] == child.state['self']
    
    # We override the master here since we can return children very quickly.
    def fetch_children(self):
        for project, path in self.model.sgfs.project_roots.iteritems():
            yield (
                project.cache_key,
                {
                    Qt.DisplayRole: project['name'],
                    Qt.DecorationRole: 'fatcow/newspaper',
                }, {
                    'Project': project,
                    'self': project,
                },
            )
    
    def add_child_menu_actions(self, node, menu):
        entity = node.state.get('self')
        if entity:
            path = self.model.sgfs.path_for_entity(entity)
            action = menu.addAction(icon('silk/folder_go', as_icon=True), 'Jump to Folder', functools.partial(call_open, path))
            if not path:
                action.setEnabled(False)
            menu.addAction(icon('silk/cog_go', as_icon=True), 'Open in Shotgun', functools.partial(call_open, entity.url))

