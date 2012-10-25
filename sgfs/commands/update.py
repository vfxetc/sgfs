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


class UpdateCommand(Command):
    """%prog [options] path [...]
    
    Update entity data.
    
    """
    
    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.add_option('-v', '--verbose', action="store_true", dest="verbose")
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        # self.add_option('-t', '--type', action="append", dest="entity_types")
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
        # entity_types = set(opts.entity_types) if opts.entity_types else None
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
                if to_dump != tag['entity']:
                    changed = True
                    tag.update({
                        'entity': to_dump,
                        'created_at': datetime.datetime.utcnow(),
                    })
            if changed or opts.verbose:
                print path
            if changed:
                if opts.verbose:
                    for tag in tags:
                        print '\t%s %d' % (tag['entity']['type'], tag['entity']['id'])
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

