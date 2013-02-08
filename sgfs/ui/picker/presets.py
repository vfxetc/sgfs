import functools

from sgfs.sgfs import SGFS
from sgfs.ui.picker.model import Model
from sgfs.ui.picker.view import ColumnView
from sgfs.ui.picker.nodes.shotgun import ShotgunEntities, ShotgunQuery, ShotgunPublishStream
from sgfs.ui.picker.utils import state_from_entity


def any_task(entity=None, path=None, sgfs=None, extra_node_types=None):
    
    sgfs = sgfs or SGFS(session=entity.session if entity else None)
    
    if path:
        entities = list(sgfs.entities_from_path(path))
    if entity:
        entities = [entity]
    
    model = Model(sgfs=sgfs)
    model.register_node_type(functools.partial(ShotgunQuery,
        entity_types=['Project', 'Asset', 'Sequence', 'Shot', 'Task'],
    ))
    for node_type in extra_node_types or ():
        model.register_node_type(node_type)

    view = ColumnView()
    view.setModel(model)
    
    if entities:
        state = state_from_entity(entities[0])
        if path:
            state['path'] = path
        initial_index = model.index_from_state(state)
        if initial_index:
            view.setCurrentIndex(initial_index)
        
    return model, view


def publishes_from_path(path, sgfs=None, publish_types=None):
    
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
    
    if True:
        model = Model(root_state=state_from_entity(entities[0].project()), sgfs=sgfs)
    else:
        model = Model(sgfs=sgfs)
    
    model.register_node_type(functools.partial(ShotgunEntities,
        entities=[entities[0].project()],
    ))
    
    model.register_node_type(functools.partial(ShotgunQuery,
        entity_types=['Asset', 'Sequence', 'Shot', 'Task'],
    ))
        
    model.register_node_type(functools.partial(ShotgunPublishStream,
        publish_types=publish_types,
    ))
        
        
    view = ColumnView()
    view.setModel(model)
        
    initial_index = model.index_from_state(state_from_entity(entities[0]))
    if initial_index:
        view.setCurrentIndex(initial_index)
        
    return model, view

