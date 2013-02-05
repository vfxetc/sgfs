from __future__ import absolute_import

import functools
import os
import fnmatch
import re

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


class TemplateGlobPicker(Node):

    def __init__(self, *args, **kwargs):
        self.entity_types = set(kwargs.pop('entity_types'))
        self.template_name = kwargs.pop('template')
        self.glob_pattern = kwargs.pop('glob')
        self.re = re.compile(fnmatch.translate(self.glob_pattern))
        super(TemplateGlobPicker, self).__init__(*args, **kwargs)

    def is_next_node(self, state):

        if 'path' in state:
            return

        if 'self' not in state:
            return

        if state['self']['type'] not in self.entity_types:
            return

        return True

    def fetch_async_children(self):

        try:
            self.root = self.model.sgfs.path_from_template(self.state['self'], self.template_name)
        except ValueError:
            return
        
        if not os.path.isdir(self.root):
            return

        for dir_name, dir_names, file_names in os.walk(self.root):
            for file_name in file_names:
                if file_name.startswith('.'):
                    continue
                if not self.re.match(file_name):
                    continue

                path = os.path.join(dir_name, file_name)
                group_names = os.path.relpath(dir_name, self.root).lstrip('.').strip('/').split('/')
                group_names = filter(None, group_names)
                groups = [(
                    name,
                    {
                        'header': name,
                        Qt.DisplayRole: name,
                        Qt.DecorationRole: 'fatcow/folder',
                    },
                    {}) for name in group_names
                ]
                yield (
                    path,
                    {
                        Qt.DisplayRole: os.path.basename(path),
                        Qt.DecorationRole: 'custom/file_extension_nk',
                        'groups': groups,
                    }, {
                        'path': path
                    }
                )

