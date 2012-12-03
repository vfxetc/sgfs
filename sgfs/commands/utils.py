"""Development script to be able to identify an entity given a variety of inputs."""

import sys
import re
import os
from pprint import pprint



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


def parse_spec(sgfs, parts, entity_types=None):
    
    # The current location.
    entity, data = _data_from_path(sgfs, os.path.abspath(os.getcwd()), entity_types)
    if not parts or parts == ['.']:
        data['__path__'] = os.path.abspath('.')
        data.update(entity)
        return data
    
    if 'project_id' not in data:
        for entity in sgfs.entities_from_path('/Volumes/VFX/Projects/Super_Buddies'):
            _expand_entity(data, entity)
    
    if 'project_id' not in data:
        raise ValueError('could not identify project from context')
        
    if len(parts) == 1:
        
        # Paths (which must have been created via Tank).
        path = os.path.abspath(parts[0])
        if os.path.exists(path):
            entity, new_data = _data_from_path(sgfs, path, entity_types)
            if new_data:
                data.update(new_data)
                data.update(entity)
                data['__path__'] = path
                return data
            
        # Shotgun detail URL.
        m = re.match(r'^https?://\w+\.shotgunstudio\.com/detail/([A-Za-z]+)/(\d+)', parts[0])
        if m:
            data.update({'type': m.group(1).title(), 'id': int(m.group(2))})
            return data
    
        # Shotgun project overview URL.
        m = re.match(r'^https?://\w+\.shotgunstudio\.com/page/\d+#([A-Z][A-Za-z]+)_(\d+)_', parts[0])
        if m:
            data.update({'type': m.group(1).title(), 'id': int(m.group(2))})
            return data
        
        # Shotgun project URL.
        m = re.match(r'^https?://\w+\.shotgunstudio\.com/page/(\d+)$', parts[0])
        if m:
            page = sgfs.session.find_one('Page', [('id', 'is', int(m.group(1)))], ['entity_type', 'project'])
            if page['entity_type'] != 'Project':
                raise ValueError('given URL is not a Project entity')
            _expand_entity(data, page['project'])
            _expand_entity(data, page)
            return data
    
    # Sequence and shot codes. E.g. `pv 7`
    if len(parts) == 2 and re.match(r'^[A-Za-z]{2}$', parts[0]) and parts[1].isdigit():
        data['sequence_code'] = parts[0].upper()
        data['shot_code'] = '%s_%03d' % (parts[0].upper(), int(parts[1]))
    
    # Direct entities. E.g. `shot 12345`
    elif len(parts) == 2 and re.match(r'^[A-Za-z]{3,}$', parts[0]) and parts[1].isdigit():
        data.update({'type': parts[0][0].upper() + parts[0][1:], 'id': int(parts[1])})
        return data
    
    # Components.
    for part in parts:
        
        # [SEQ_]SHOT[_REUSE] codes.
        m = re.match(r'^(?:([A-Za-z]{2})_)?(\d+)(?:_(\d+))?$', part)
        if m:
            seq, shot, reuse = m.groups()
                        
            if seq or reuse:
                if seq:
                    data['sequence_code'] = seq.upper()
                    data.pop('sequence_id', None)
                if reuse:
                    data['reuse_number'] = int(reuse)
                data['shot_number'] = int(shot)
                continue
            
            if 'shot_number' not in data:
                data['shot_number'] = int(shot)
            else:
                data['reuse_number'] = int(shot)
            continue
        
        # Sequences by themselves..
        if len(part) == 2:
            data['sequence_code'] = part.upper()
            data.pop('sequence_id', None)
            continue
        
        raise ValueError('could not parse part %r' % part)
        # TODO: task, asset_type, asset_name
    
    # Start with shot since it is most specific.
    if 'shot_number' in data:
        data.setdefault('reuse_number', 1)
        
        if 'sequence_id' in data:
            shot = sgfs.session.find_one('Shot', [
                ('code', 'ends_with', '_%(shot_number)03d_%(reuse_number)03d' % data),
                ('sg_sequence', 'is', {'type': 'Sequence', 'id': data['sequence_id']}),
            ])
            data.update(shot)
            return data
        
        if 'sequence_code' in data:
            shot = sgfs.session.find_one('Shot', [
                ('code', 'is', '%(sequence_code)s_%(shot_number)03d_%(reuse_number)03d' % data),
                ('project', 'is', {'type': 'Project', 'id': data['project_id']}),
            ])
            data.update(shot)
            return data
        
        raise ValueError('shot without sequence')
        
        code = '%(sequence_code)s_%(shot_number)03d_%(reuse_number)03d' % data
        shot = sgfs.session.find_one('Shot', [('code', 'is', code), ('project', 'is', {'type': 'Project', 'id': data['project_id']})])
        data.update(shot)
        return data
    
    # Sequence.
    if 'sequence_id' in data:
        data.update({'type': 'Sequence', 'id': data['sequence_id']})
        return data
    
    if 'sequence_code' in data:
        seq = sgfs.session.find_one('Sequence', [
            ('code', 'is', data['sequence_code']),
            ('project', 'is', {'type': 'Project', 'id': data['project_id']}),
        ])
        data.update(seq)
        return data
    
    # We didn't identify anything.
    return data







if __name__ == '__main__':
    pprint(parse(sys.argv[1:]))
