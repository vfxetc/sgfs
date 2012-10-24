import os
from subprocess import call

from . import Command
from . import utils

class OpenCommand(Command):
    """%prog [options] [paths]
    
    Open the specified entity. Can give paths, Shotgun URLs, sequence or shot
    codes.
    
    """
    
    def __init__(self):
        super(OpenCommand, self).__init__()
        self.add_option('-t', '--types', action="append", dest="entity_types", help="entity types to find if given a path")
        
    def run(self, sgfs, opts, args):
        
        entity_types = [x.title() for x in opts.entity_types] if opts.entity_types else None
        data = utils.parse_spec(sgfs, args, entity_types)
        
        type_ = data.get('type')
        id_ = data.get('id')
        
        if not (type_ or id_):
            print 'no entities found'
            return
        
        url = sgfs.session.shotgun.base_url + '/detail/%s/%s' % (type_, id_)
        print url
        call(['open', url])


main = OpenCommand()