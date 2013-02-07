from __future__ import absolute_import

import functools
import threading

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs.ui.picker.utils import debug, icon, call_open
from sgfs.ui.picker.nodes.base import Node


class ShotgunBase(Node):
    
    backrefs = {
        'Asset': [('Project', 'project')],
        'HumanUser': [None],
        'Project': [None],
        'PublishEvent': [('Task', 'sg_link')],
        'Sequence': [('Project', 'project')],
        'Shot': [('Sequence', 'sg_sequence')],
        'Task': [('Shot', 'entity'), ('Asset', 'entity')],
        'Ticket': [('Tool', 'sg_tool')],
        'Tool': [('Project', 'project')],
        'Version': [('Shot', 'entity'), ('Task', 'sg_task')],
        'Step': [None],
        'ActionMenuItem': [None],
        'EventLogEntry': [('Project', 'entity'), ('Sequence', 'entity'), ('Shot', 'entity')],
    }
    
    labels = {
        'Project': ['{Project[name]}'],
        'HumanUser': ['{HumanUser[email]}'],
        'Sequence': ['{Sequence[code]}'],
        'Asset': ['{Asset[sg_asset_type]}', '{Asset[code]}'],
        'Shot': ['{Shot[code]}'],
        'Task': ['{Task[step][code]}', '{Task[content]}'],
        'PublishEvent': ['{PublishEvent[sg_type]}', '{PublishEvent[code]}', 'v{PublishEvent[sg_version]:04d}'],
        'Tool': ['{Tool[code]}'],
        'Ticket': ['{Ticket[title]}'],
        'Version': ['{Version[code]}'],
        'Step': ['{self[entity_type]}', '{Step[code]}'],
        'ActionMenuItem': ['{self[title]} ({self[entity_type]})'],
        'EventLogEntry': ['{self[event_type]} - {self[attribute_name]}']
    }
    
    headers = {
        'Asset': ['Asset Type'],
        'PublishEvent': ['Publish Type', 'Publish Name', 'Publish Version'],
        'Task': ['Step'],
    }
    
    icons = {
        'Sequence': 'fatcow/film_link',
        'Shot': 'fatcow/film',
        'PublishEvent': 'fatcow/brick',
        'Asset': 'fatcow/box_closed',
        'Version': 'fatcow/images',
        'Project': 'fatcow/newspaper',
    }
    
    fields = {
        'Task': ['step.Step.color', 'task_assignees'],
        'Step': ['code', 'color', 'entity_type'],
        'Tool': ['code'],
        'Ticket': ['title'],
        'HumanUser': ['firstname', 'lastname', 'email'],
        'Version': ['code'],
        'ActionMenuItem': ['title', 'entity_type'],
        'EventLogEntry': ['event_type', 'attribute_name']
    }
    
    def _child_tuple_from_entity(self, entity, strict_format=False):
        
        type_ = entity['type']
        
        font = None
        if type_ == 'Task' and 'task_assignees' in entity and self.model.sgfs.session.guess_user() in entity['task_assignees']:
            font = QtGui.QFont()
            font.setUnderline(True)
        
        labels = []
        for format_string in self.labels[type_]:
            state = dict(self.state)
            state[type_] = entity
            state['self'] = entity
            try:
                labels.append(format_string.format(**state))
            except KeyError as e:
                if strict_format:
                    raise
                debug('formatting error: %s', e)
                labels.append('%r %% %r' % (format_string, entity))
        
        headers = []
        for format_string in self.headers.get(type_, []):
            state = dict(self.state)
            state[type_] = entity
            try:
                headers.append(format_string.format(**state))
            except KeyError as e:
                if strict_format:
                    raise
                debug('formatting error: %s', e)
                headers.append('%r %% %r' % (format_string, entity))
        
        # Add some default headers.
        headers.extend(labels[len(headers):-1])
        headers.append(type_)
        
        groups = []
        
        # Entity type group.
        if hasattr(self, 'active_types') and len(self.active_types) > 1:
            groups.append((
                ('group', type_),
                {
                    Qt.DisplayRole: type_ + 's',
                    Qt.DecorationRole: self.icons.get(type_),
                    'header': 'Entity Type',
                },
                {}
            ))
        
        # All but the last label is a group.
        for i, label in enumerate(labels[:-1]):
            groups.append((
                ('group', type_, label),
                {
                    Qt.DisplayRole: label,
                    Qt.DecorationRole: self.icons.get(type_),
                    Qt.FontRole: font,
                    'header': headers[i],
                }, {
                    '%s.groups[%d]' % (type_, i): label
                }
            ))
        
        view_data = {
            Qt.DisplayRole: labels[-1],
            Qt.FontRole: font,
            'header': headers[len(labels) - 1],
            'groups': groups,
        }
        
        if entity.get('step') and entity['step'].fetch('color'):
            color = QtGui.QColor.fromRgb(*(int(x) for x in entity['step']['color'].split(',')))
            for group in groups:
                group[1][Qt.DecorationRole] = color
            view_data[Qt.DecorationRole] = color
        
        if entity['type'] in self.icons:
            view_data[Qt.DecorationRole] = self.icons[entity['type']]

        new_state = {
            entity['type']: entity,
            'self': entity,
        }
        
        return entity.cache_key, view_data, new_state
    
    def filters(self, entity_type):
        filters = []
        for backref in self.backrefs[entity_type]:
            if backref and backref[0] in self.state:
                filters.append((backref[1], 'is', self.state[backref[0]]))
        return filters
    
    def add_child_menu_actions(self, node, menu):
        entity = node.state.get('self')
        if entity:
            path = self.model.sgfs.path_for_entity(entity)
            action = menu.addAction(icon('silk/folder_go', as_icon=True), 'Jump to Folder', functools.partial(call_open, path))
            if not path:
                action.setEnabled(False)
            menu.addAction(icon('silk/cog_go', as_icon=True), 'Open in Shotgun', functools.partial(call_open, entity.url))




class ShotgunQuery(ShotgunBase):
    
    _getting_user = False
    
    def __init__(self, *args, **kwargs):
        self.entity_types = kwargs.pop('entity_types')
        super(ShotgunQuery, self).__init__(*args, **kwargs)
        
        # Spawn a thread to grab the human user.
        if not self._getting_user and 'Task' in self.entity_types:
            self._user_thread = threading.Thread(target=self.model.sgfs.session.guess_user)
            self._user_thread.start()
            ShotgunQuery._getting_user = True
    
    def __repr__(self):
        return '<%s for %r at 0x%x>' % (self.__class__.__name__, self.active_types, id(self))
    
    def is_next_node(self, state):
        
        # If any types have a backref that isn't satisfied.
        self.active_types = []
        for type_ in self.entity_types:
            
            # We don't want to see this state again.
            if type_ in state:
                continue
            
            for backref in self.backrefs[type_]:
                
                # No backrefs mount on an empty state.
                if backref is None and not state:
                    self.active_types.append(type_)
                    continue
                
                # The last step must have set our backref.
                if backref and backref[0] == state.get('self', {}).get('type'):
                    self.active_types.append(type_)
        
        return bool(self.active_types)
    
    def child_matches_initial_state(self, child, init_state):
        
        last_entity = child.state.get('self')
        # debug('entity %r', last_entity)
        # debug('state %r', init_state)
        if not last_entity:
            return
        
        if last_entity['type'] not in self.active_types:
            return
        
        return last_entity == init_state.get(last_entity['type'])
    
    def get_temp_children_from_state(self, init_state):
        for type_ in self.active_types:
            if type_ in init_state:
                entity = init_state[type_]
                for backref in self.backrefs[type_]:
                    if backref is None or (entity.get(backref[1]) and entity[backref[1]] == self.state.get(backref[0])):
                        yield self._child_tuple_from_entity(entity)
                        return
    
    def fetch_children(self):
        # # Fetch from local SGFS caches.
        # for type_ in self.active_types:
        #    self.schedule_async_fetch(self.fetch_local_children, type_)
        for type_ in self.active_types:
            self.schedule_async_fetch(self.fetch_remote_children, type_)
    
    def fetch_local_children(self, type_):
        for backref in self.backrefs[type_]:
            if not backref or backref[0] not in self.state:
                continue
            parent_directory = (
                self.state.get('%s.path' % backref[0]) or
                self.model.sgfs.path_for_entity(self.state[backref[0]])
            )
            if not parent_directory:
                return
            for path, entity in self.model.sgfs.entities_in_directory(parent_directory, type_, load_tags=True):
                try:
                    key, view, state = self._child_tuple_from_entity(entity, strict_format=True)
                except KeyError:
                    continue
                state['%s.path' % type_] = path
                yield key, view, state
        
    def fetch_remote_children(self, type_):
        for entity in self.fetch_entities(type_):
            yield self._child_tuple_from_entity(entity)

    def fetch_entities(self, entity_type):
        filters = self.filters(entity_type)
        fields = self.fields.get(entity_type) or []
        res = self.model.sgfs.session.find(
            entity_type,
            filters,
            fields,
        )
        return res


class ShotgunPublishStream(ShotgunQuery):

    single_labels = {'PublishEvent': ['{self[code]}', 'v{self[sg_version]:04d}']}
    single_headers = {'PublishEvent': ['Publish Name', 'Version']}

    multi_labels = {'PublishEvent': ['{self[sg_type]}', '{self[code]}', 'v{self[sg_version]:04d}']}
    multi_headers = {'PublishEvent': ['Publish Type', 'Name', 'Version']}
    
    def __init__(self, *args, **kwargs):
        
        self.publish_types = kwargs.pop('publish_types', None) or kwargs.pop('publish_type', None)
        if isinstance(self.publish_types, basestring):
            self.publish_types = [self.publish_types]
        if self.publish_types is None or len(self.publish_types) > 1:
            self.labels = self.multi_labels
            self.headers = self.multi_headers
        else:
            self.labels = self.single_labels
            self.headers = self.single_headers
        
        kwargs.setdefault('entity_types', ['PublishEvent'])
        super(ShotgunPublishStream, self).__init__(*args, **kwargs)
    
    def filters(self, entity_type):
        filters = super(ShotgunPublishStream, self).filters(entity_type)
        filters.append(('sg_version', 'greater_than', 0))
        if self.publish_types:
            # This isn't documented to work, but apparently it does. Go figure.
            filters.append(('sg_type', 'in') + tuple(self.publish_types))
        return filters

class ShotgunEntities(ShotgunBase):
    
    def __init__(self, *args, **kwargs):
        self.entities = kwargs.pop('entities')
        self.header = kwargs.pop('header', 'Context')
        super(ShotgunEntities, self).__init__(*args, **kwargs)
    
    def is_next_node(self, state):
        return not state
    
    def update(self, view_data, state):
        view_data['header'] = self.header
        super(ShotgunEntities, self).update(view_data, state)
        
    def child_matches_initial_state(self, child, init_state):
        entity = child.state['self']
        return init_state.get(entity['type']) == entity
    
    def fetch_children(self, *args):
        return [self._child_tuple_from_entity(e) for e in self.entities]
    
    def sort_children(self):
        pass

