from subprocess import call
import optparse
import os
import platform

from shotgun_api3_registry import connect
from sgfs import SGFS


def sgaction(entity_type, selected_ids, project_id, **kwargs):
    
    root = os.environ.get('KS_PROJECTS')
    if not root:
        optparser.error('$KS_PROJECTS must be set')
    sgfs = SGFS(root, shotgun=connect())
    
    paths = []
    
    for id_ in selected_ids:
        entity = sgfs.session.merge(dict(type=entity_type, id=id_))
        path = sgfs.path_for_entity(entity)
        if path:
            print entity, '->', repr(path)
            paths.append(path)
    
    if not paths:
        print 'No paths for %s %s' % (entity_type, selected_ids)
        return
    
    for path in set(paths):
        if platform.system() == 'Darwin':
            call(['open', path])
        else:
            call(['xdg-open', path])

    