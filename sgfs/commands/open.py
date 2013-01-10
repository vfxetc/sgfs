from subprocess import call
import platform

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
        data = utils.parse_spec(sgfs, args, entity_types)
        
        type_ = data.get('type')
        id_ = data.get('id')
        
        if not (type_ or id_):
            print 'no entities found'
            return
        
        getattr(self, self.method_name)(sgfs, type_, id_, data)
    
    def open(self, x):
        if platform.system() == 'Darwin':
            call(['open', x])
        else:
            call(['xdg-open', x])
        
    def open_shotgun(self, sgfs, type_, id_, data):
        
        url = sgfs.session.shotgun.base_url + '/detail/%s/%s' % (type_, id_)
        print url
        self.open(url)
    
    def open_directory(self, sgfs, type_, id_, data):
        
        path = data.get('__path__') or sgfs.path_for_entity({'type': type_, 'id': id_})
        print path
        self.open(path)
    
    def print_path(self, sgfs, type_, id_, data):
        
        path = data.get('__path__') or sgfs.path_for_entity({'type': type_, 'id': id_})
        print path


run_open = OpenCommand('open_directory')
run_shotgun = OpenCommand('open_shotgun')
run_path = OpenCommand('print_path')

