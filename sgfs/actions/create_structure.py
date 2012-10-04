import optparse
import os

from shotgun_api3_registry import connect
from sgfs import SGFS

from sgactions.utils import notify


def run_create(**kwargs):
    _run(False, **kwargs)

def run_preview(**kwargs):
    _run(True, **kwargs)

def _run(dry_run, entity_type, selected_ids, **kwargs):
    
    sgfs = SGFS()
    
    entities = sgfs.session.merge([dict(type=entity_type, id=id_) for id_ in selected_ids])
    heirarchy = sgfs.session.fetch_heirarchy(entities)
    sgfs.session.fetch_core(heirarchy)
    
    commands = sgfs.create_structure(entities, dry_run=dry_run)
    
    notify(
        title='Preview Folders' if dry_run else 'Creating Folders',
        message='\n'.join(commands) or 'Everything is up to date.',
    )
