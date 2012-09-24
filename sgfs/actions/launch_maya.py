from subprocess import call
import optparse
import os
import platform

from shotgun_api3_registry import connect
from sgfs import SGFS

from . import notify


def run(entity_type, selected_ids, **kwargs):
    
    sgfs = SGFS()
    paths = []
    
    if not selected_ids:
        notify('Must select Task to launch Maya')
        return
    
    entity = sgfs.session.merge(dict(type=entity_type, id=selected_ids[0]))
    path = sgfs.path_for_entity(entity)
    
    if not path:
        notify('No folders for %s %s' % (entity['type'], entity['id']))
        return
    
    print entity, '->', repr(path)
    
    call(['maya_launcher'], cwd=path)

    