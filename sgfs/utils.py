
parent_fields = {
    'Task': 'entity',
    'Shot': 'sg_sequence',
    'Sequence': 'project',
    'Asset': 'project',
    'Project': None,
}

def parent(entity):
    return entity.get(parent_fields.get(entity['type']))
