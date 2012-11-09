import functools

from ...sgfs import SGFS
from .model import Model
from .view import ColumnView
from .nodes.shotgun import ShotgunEntities, ShotgunQuery, ShotgunPublishStream
from .utils import state_from_entity

__also_reload__ = [
    '...sgfs',
    '.model',
    '.view',
    '.utils',
    '.nodes.shotgun',
]


def publishes_from_path(path, sgfs=None):
    
    sgfs = sgfs or SGFS()
    
    entities = list(sgfs.entities_from_path(path))
    if not entities:
        raise RuntimeError('No entities for workspace.')
        
    sgfs.session.fetch_heirarchy(entities)
    for entity in list(entities):
        entity = entity.parent()
        while entity and entity not in entities:
            entities.append(entity)
            entity = entity.parent()
    
    model = Model(sgfs=sgfs)
    
    model.register_node_type(functools.partial(ShotgunEntities,
        entities=[entities[0].project()],
    ))
        
    is_sequence_pipeline = any(e['type'] == 'Sequence' for e in entities)
    entity_types = (
        ['Sequence', 'Shot', 'Task']
        if is_sequence_pipeline else
        ['Asset', 'Task']
    )
    model.register_node_type(functools.partial(ShotgunQuery,
        entity_types=entity_types,
    ))
        
    model.register_node_type(ShotgunPublishStream)
        
    initial_index = model.index_from_state(state_from_entity(entities[0]))
        
    view = ColumnView()
    view.setColumnWidths([150, 150, 150, 150, 200, 300])
    view.setMaximumWidth(sum([150, 150, 150, 150, 200, 300]) + 6)
    view.setPreviewVisible(False)
    view.setModel(model)
        
    if initial_index:
        view.setCurrentIndex(initial_index)
        
    return model, view