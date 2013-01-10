from subprocess import call

from . import Command


class RelinkCommand(Command):
    """%prog [options] path
    
    Find and relink entities into the SGFS cache.
    
    """
    
    def __init__(self):
        super(RelinkCommand, self).__init__()
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        self.add_option('-u', '--update', action="store_true", dest="update")
        self.add_option('-n', '--dry-run', action="store_true", dest="dry_run")
        
    def run(self, sgfs, opts, args, recurse=False, **kwargs):
        if len(args) != 1:
            self.print_usage()
            return 1
        changed = sgfs.rebuild_cache(args[0], recurse=recurse or opts.recurse, dry_run=opts.dry_run)
        for old, new, tag in changed:
            print old or '<does not exist>'
            print new
            print
        
        if opts.update and changed:
            if opts.dry_run:
                print 'Checking for tag updates (without applying)...'
            else:
                print 'Updating tags...'
            cmd = ['sgfs-update']
            if opts.dry_run:
                cmd.append('--dry-run')
            cmd.extend(new for old, new, tag in changed)
            call(cmd)
        


main = RelinkCommand()

