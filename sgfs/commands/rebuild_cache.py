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
    
    root = os.environ.get('KS_PROJECTS')
    if not root:
        optparser.error('$KS_PROJECTS must be set')
    sgfs = SGFS(root, shotgun=connect())
    
    sgfs.rebuild_cache(os.path.abspath(args[0]))
    
    
