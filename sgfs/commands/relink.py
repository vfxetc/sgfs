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
        self.add_option('-v', '--verbose', action="store_true", dest="verbose")
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        
    def run(self, sgfs, opts, args, recurse=False, **kwargs):
        if len(args) != 1:
            self.print_usage()
            return 1
        sgfs.rebuild_cache(args[0], recurse=recurse or opts.recurse, verbose=opts.verbose)


main = RelinkCommand()

