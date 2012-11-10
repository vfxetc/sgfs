from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from ..utils import debug
from .base import Node


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
