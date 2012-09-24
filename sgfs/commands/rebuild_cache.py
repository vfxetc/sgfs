import optparse
import os

from shotgun_api3_registry import connect
from sgfs import SGFS


def main():
    
    optparser = optparse.OptionParser(
        usage="%prog path"
    )

    opts, args = optparser.parse_args()
    if len(args) != 1:
        optparser.print_usage()
        exit(1)
    
    sgfs = SGFS()
    sgfs.rebuild_cache(os.path.abspath(args[0]))
    
