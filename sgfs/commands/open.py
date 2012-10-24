import os
from subprocess import call

from . import Command

class OpenCommand(Command):
    """%prog [options] [paths]
    
    Open the entities tagged in the given path in Shotgun.
    
    """
    
    def __init__(self):
        super(OpenCommand, self).__init__()
        self.add_option('-a', '--all', action="store_true", help="open all pages, or just the first")
        self.add_option('-t', '--types', action="append", dest="entity_types", help="entity types to find")
        
    def run(self, sgfs, opts, args):
        
        entity_types = [x.title() for x in opts.entity_types] if opts.entity_types else None
        paths = [os.path.abspath(x) for x in (args or ['.'])]
        
        opened = set()
        
        for path in paths:
            for entity in sgfs.entities_from_path(path, entity_type=entity_types):
                
                if entity in opened:
                    continue
                opened.add(entity)
                
                url = sgfs.session.shotgun.base_url + '/detail/%s/%s' % (entity['type'], entity['id'])
                print url
                call(['open', url])
                
                if not opts.all:
                    return
        
        if not opened:
            print 'no entities found'
        
        
main = OpenCommand()