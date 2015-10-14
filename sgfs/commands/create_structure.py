from subprocess import call
import sys

from . import Command
from . import utils


class CreateStructureCommand(Command):
    """%prog [options] [paths]
    
    Open or print the specified entity. Can give paths, Shotgun URLs, sequence or shot
    codes.
    
    """
    
    def __init__(self):
        super(CreateStructureCommand, self).__init__()
        self.add_option('-n', '--dry-run', action='store_true', help='don\'t actually do anything')
        self.add_option('-v', '--verbose', action='store_true', help='show everything being done')
        self.add_option('-t', '--types', action="append", dest="entity_types", help="entity types to find if given a path")
        
    def run(self, sgfs, opts, args):
        
        entity_types = [x.title() for x in opts.entity_types] if opts.entity_types else None
        
        entities = []
        for arg in args:
            entity = utils.parse_spec(sgfs, arg, entity_types)
            if 'type' not in entity or 'id' not in entity:
                print >> sys.stderr, 'no entities found for', arg
            entities.append(entity)
        
        sgfs.create_structure(entities, dry_run=opts.dry_run, verbose=opts.verbose or opts.dry_run)


main = CreateStructureCommand()
