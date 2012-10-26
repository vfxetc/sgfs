import optparse
import os
import yaml
from subprocess import call
import datetime
import sys

from shotgun_api3_registry import connect
from sgfs import SGFS


import os
from subprocess import call
import platform

from . import Command
from . import utils


def iter_entity_delta(a, b):
    """Determine the deep diferences bettween two entities.
    
    This function ignores ``updated_at``, and currently cannot deal with lists.
    
    Yields ``(name, left_value, right_value)``, where either value may be ``None``
    if it was not present.
    
    """
    
    a = dict(a)
    a.pop('updated_at', None)
    
    for k, v in b.iteritems():
        
        if k == 'updated_at':
            continue
        
        if k not in a:
            yield k, None, v
            continue
        
        # This doesn't distinguish bettween entities and dicts. Oh well.
        if isinstance(v, dict):
            for n, x, y in iter_entity_delta(a.pop(k), v):
                yield k + '.' + n, x, y
            continue
        
        av = a.pop(k)
        if av != v:
            yield k, av, v
    
    for k, v in a.iteritems():
        yield k, v, None
    
    
class UpdateCommand(Command):
    """%prog [options] path [...]
    
    Update entity data.
    
    """
    
    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.add_option('-v', '--verbose', action="store_true", dest="verbose")
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        self.add_option('-n', '--dry-run', action="store_true", dest="dry_run")
        self.add_option('-f', '--field', action='append', dest="fields")
        
    def run(self, sgfs, opts, args):
        
        if not args:
            if not os.isatty(0):
                args = [x.strip() for x in sys.stdin]
                args = [x for x in args if x]
            else:
                self.print_usage()
                return 1
        
        # Collect all the existing data.
        tags_by_path = {}
        if opts.recurse:
            for arg in args:
                for path, tag in sgfs.entity_tags_in_directory(arg, merge_into_session=False):
                    tags_by_path.setdefault(path, []).append(tag)
        else:
            for arg in args:
                for tag in sgfs.get_directory_entity_tags(arg, merge_into_session=False):
                    tags_by_path.setdefault(arg, []).append(tag)
        
        # Merge all the data.
        entities = dict()
        for path, tags in tags_by_path.iteritems():
            for tag in tags:
                entity = sgfs.session.merge(tag['entity'])
                entities[entity.cache_key] = entity
        
        # Fetch all the core and requested data.
        sgfs.session.fetch(entities.itervalues(), opts.fields or [], force=True)
        
        for path, tags in sorted(tags_by_path.iteritems()):
            changed = False
            for tag in tags:
                
                entity = entities[(tag['entity']['type'], tag['entity']['id'])]
                to_dump = entity.as_dict()
                changes = list(iter_entity_delta(tag['entity'], to_dump))
                
                if changes:
                    
                    if not changed:
                        print path
                    print '\t%s %d:' % (to_dump['type'], to_dump['id'])
                        
                    changed = True
                    
                    if opts.verbose:
                        for name, old, new in changes:
                            print '\t\t%s: %r -> %r' % (name, old, new)
                    
                    tag.update({
                        'entity': to_dump,
                        'created_at': datetime.datetime.utcnow(),
                    })
            
            if opts.dry_run:
                continue
            
            if changed:
                serialized = yaml.dump_all(tags,
                    explicit_start=True,
                    indent=4,
                    default_flow_style=False
                )
                call(['cp', os.path.join(path, '.sgfs.yml'), os.path.join(path, '.sgfs.%s.yml' % datetime.datetime.utcnow().strftime('%y%m%d.%H%M%S.%f'))])
                with open(os.path.join(path, '.sgfs.yml'), 'w') as fh:
                    fh.write(serialized)

            # print path

main = UpdateCommand()

