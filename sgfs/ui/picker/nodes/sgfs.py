from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from .base import Node


class SGFSRoots(Node):
    
    def update(self, *args):
        super(SGFSRoots, self).update(*args)
        self.view_data.setdefault('header', 'SGFS Project')
        
    @staticmethod
    def is_next_node(state):
        return 'Project' not in state
    
    def child_matches_initial_state(self, state, init_state):
        return 'Project' in state and state['Project'] == init_state.get('Project')
    
    def fetch_children(self, init_state):
        for project, path in sorted(self.model.sgfs.project_roots.iteritems(), key=lambda x: x[0]['name']):
            yield (
                project.cache_key,
                {
                    Qt.DisplayRole: project['name'],
                    Qt.DecorationRole: '/home/mboers/Documents/icons/fatcow/16x16/newspaper.png',
                }, {
                    'Project': project,
                },
            )
