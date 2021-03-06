from subprocess import call
import sys

from sgfs import SGFS

from sgactions.utils import notify


def run(entity_type, selected_ids, **kwargs):
    
    sgfs = SGFS()
    paths = []
    
    for id_ in selected_ids:
        entity = sgfs.session.merge(dict(type=entity_type, id=id_))
        path = sgfs.path_for_entity(entity)
        if path:
            print entity, '->', repr(path)
            paths.append(path)
    
    if not paths:
        notify('No paths for %s %s' % (entity_type, selected_ids))
        return
    
    notify('Opened ' + ', '.join(sorted(paths)))
    
    for path in set(paths):
        if sys.platform.startswith('darwin'):
            call(['open', path])
        else:
            call(['xdg-open', path])

