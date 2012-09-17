import optparse
import os

from shotgun_api3_registry import connect
from sgfs import SGFS


def create_sgaction(**kwargs):
    _sgaction(False, **kwargs)

def preview_sgaction(**kwargs):
    _sgaction(True, **kwargs)

def _sgaction(dry_run, entity_type, selected_ids, **kwargs):
    
    root = os.environ.get('KS_PROJECTS')
    if not root:
        optparser.error('$KS_PROJECTS must be set')
    sgfs = SGFS(root, shotgun=connect())
    
    entities = sgfs.session.merge([dict(type=entity_type, id=id_) for id_ in selected_ids])
    heirarchy = sgfs.session.fetch_heirarchy(entities)
    sgfs.session.fetch_core(heirarchy)
    
    commands = sgfs.create_structure(entities, dry_run=dry_run)
    print '\n'.join(commands)
