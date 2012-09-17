import optparse
import os

from shotgun_api3_registry import connect
from sgfs import SGFS


def main():
    
    optparser = optparse.OptionParser(
        usage="%prog [options] entity_type id path"
    )
    optparser.add_option('--nocache', dest='cache', default=True, action='store_false',
        help='Do not add this path to the project level cache.'
    )
    
    opts, args = optparser.parse_args()
    if len(args) != 3:
        optparser.print_usage()
        exit(1)
    
    entity_type, entity_id, path = args
    try:
        entity_id = int(entity_id)
    except ValueError:
        optparser.error('entity_id must be an integer')
    
    root = os.environ.get('KS_PROJECTS')
    if not root:
        optparser.error('$KS_PROJECTS must be set')
    sgfs = SGFS(root, shotgun=connect())
    
    entity = sgfs.session.merge(dict(type=entity_type, id=entity_id))
    entities = entity.fetch_heirarchy()
    sgfs.session.fetch_core(entities)
    sgfs.tag_directory_with_entity(path, entity, cache=opts.cache)
    