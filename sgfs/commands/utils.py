"""Development script to be able to identify an entity given a variety of inputs."""

import os
import re


def _expand_entity(data, entity, seen=None):
    
    if seen is None:
        seen = set()
    if entity in seen:
        return
    seen.add(entity)
    
    _type = entity['type'].lower()
    data['type'] = entity['type']
    data['id'] = entity['id']
    
    for k, v in entity.iteritems():
        if k != 'type':
            data.setdefault(_type + '_' + k, v)
        if isinstance(v, dict):
            _expand_entity(data, v, seen)


def _data_from_path(sgfs, path, entity_types=None):
    data = {}
    entities = sgfs.entities_from_path(path, entity_type=entity_types)
    for entity in entities:
        _expand_entity(data, entity)
    return (entities[0] if entities else None, data)


def parse_spec(sgfs, spec, entity_types=None, project_from_page=False):

    # We used to accept multiple parameters, but now we just take one.
    if not isinstance(spec, str):
        if not spec:
            spec = '.'
        elif len(spec) == 1:
            spec = spec[0]
        else:
            raise TypeError('spec must be string or single-item list; got %r' % spec)

    # Paths (which must have been created via Tank).
    path = os.path.abspath(spec)
    if os.path.exists(path):
        entity, data = _data_from_path(sgfs, path, entity_types)
        if data:
            data.update(entity)
            data['__path__'] = path
            return sgfs.session.merge(data)
        else:
            raise ValueError('got not entities from path')
        
    # Shotgun detail URL.
    m = re.match(r'^https?://\w+\.shotgunstudio\.com/detail/([A-Za-z]+)/(\d+)', spec)
    if m:
        return sgfs.session.merge({'type': m.group(1).title(), 'id': int(m.group(2))})

    # Shotgun project overview URL.
    m = re.match(r'^https?://\w+\.shotgunstudio\.com/page/\d+#([A-Z][A-Za-z]+)_(\d+)_', spec)
    if m:
        return sgfs.session.merge({'type': m.group(1).title(), 'id': int(m.group(2))})
    
    # Shotgun project URL.
    m = re.match(r'^https?://\w+\.shotgunstudio\.com/page/(\d+)$', spec)
    if m:
        page = sgfs.session.find_one('Page', [('id', 'is', int(m.group(1)))], ['entity_type', 'project'])
        if page['entity_type'] != 'Project':
            if project_from_page and page.get('project'):
                return page['project']
            raise ValueError('given URL is not a Project entity')
        data = {}
        _expand_entity(data, page['project'])
        _expand_entity(data, page)
        return sgfs.session.merge(data)
        
    # Direct entities. E.g. `shot 12345`
    m = re.match(r'^([A-Za-z]{3,}):(\d+)$', spec)
    if m:
        type_, id_ = m.groups()
        return sgfs.session.merge({
            'type': type_[0].upper() + type_[1:],
            'id': int(id_),
        })
    
    # TODO: do something with templates.
    
    raise ValueError('nothing useful found for %r' % spec)
