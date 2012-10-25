import optparse
import os

from shotgun_api3_registry import connect
from sgfs import SGFS


import os
from subprocess import call
import platform

from . import Command
from . import utils


class RelinkCommand(Command):
    """%prog [options] path
    
    Find and relink entities into the SGFS cache.
    
    """
    
    def __init__(self):
        super(RelinkCommand, self).__init__()
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        self.add_option('-u', '--update', action="store_true", dest="update")
        
    def run(self, sgfs, opts, args, recurse=False, **kwargs):
        if len(args) != 1:
            self.print_usage()
            return 1
        changed = sgfs.rebuild_cache(args[0], recurse=recurse or opts.recurse)
        for old, new, tag in changed:
            print new
        
        if opts.update and changed:
            print 'updating tags...'
            cmd = ['sgfs-update']
            cmd.extend(new for old, new, tag in changed)
            call(cmd)


main = RelinkCommand()

