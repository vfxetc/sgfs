from subprocess import call
import sys

from . import Command
from . import utils

class OpenCommand(Command):
    """%prog [options] [paths]
    
    Open or print the specified entity. Can give paths, Shotgun URLs, sequence or shot
    codes.
    
    """
    
    def __init__(self, method_name):
        super(OpenCommand, self).__init__()
        self.method_name = method_name
        self.add_option('-t', '--types', action="append", dest="entity_types", help="entity types to find if given a path")
        
    def run(self, sgfs, opts, args):
        entity_types = [x.title() for x in opts.entity_types] if opts.entity_types else None
        entity = utils.parse_spec(sgfs, args, entity_types)
        if not entity:
            print >> sys.stderr, 'no entities found'
            return
        getattr(self, self.method_name)(sgfs, entity)
    
    def open(self, x):
        if sys.platform.startswith('darwin'):
            call(['open', x])
        else:
            call(['xdg-open', x])
        
    def open_shotgun(self, sgfs, entity):
        url = sgfs.session.shotgun.base_url + '/detail/%s/%s' % (entity['type'], entity['id'])
        print url
        self.open(url)
    
    def open_directory(self, sgfs, entity):
        path = sgfs.path_for_entity(entity) or entity.get('__path__')
        if path:
            print path
            self.open(path)
        else:
            print >> sys.stderr, 'no path for', entity.minima;
    
    def print_path(self, sgfs, entity):
        path = sgfs.path_for_entity(entity) or entity.get('__path__')
        if path:
            print path
        else:
            print >> sys.stderr, 'no path for', entity.minimal


run_open = OpenCommand('open_directory')
run_shotgun = OpenCommand('open_shotgun')
run_path = OpenCommand('print_path')

