import os

from sgsession.utils import parse_isotime

from . import Command


class RepairCommand(Command):
    """%prog [options] path+
    
    Find and relink entities into the SGFS cache.
    
    """
    
    def __init__(self):
        super(RepairCommand, self).__init__()
        self.add_option('-r', '--recurse', action="store_true", dest="recurse")
        self.add_option('-n', '--dry-run', action="store_true", dest="dry_run")
        self.add_option('-v', '--verbose', action="store_true", dest="verbose")
        
    def run(self, sgfs, opts, args, recurse=False, **kwargs):

        if not args:
            self.print_usage()
            return 1

        for root in args:
            root = os.path.abspath(root)

            for path, dir_names, file_names in os.walk(root):
                tags = sgfs._read_directory_tags(path)
                if not tags:
                    continue
                if opts.verbose:
                    print 'checking', path

                tags, repair_count = self.repair_tags(tags)
                if repair_count:
                    print 'REPAIRED', path
                    if not opts.dry_run:
                        sgfs._write_directory_tags(path, tags, replace=True)

    def repair_tags(self, data):

        repair_count = 0

        if isinstance(data, (list, tuple)):
            new = []
            for x in data:
                x, new_count = self.repair_tags(x)
                new.append(x)
                repair_count += new_count
            return new, repair_count

        if isinstance(data, dict):
            if 'type' in data and 'id' in data:
                for key in 'updated_at', 'created_at':
                    value = data.get(key)
                    if value and isinstance(value, basestring):
                        data[key] = parse_isotime(value)
                        repair_count += 1
            new = {}
            for key, value in data.iteritems():
                new[key], new_count = self.repair_tags(value)
                repair_count += new_count
            return new, repair_count

        return data, 0

        


main = RepairCommand()

def main_rebuild(*args, **kwargs):
    kwargs['recurse'] = True
    return main(*args, **kwargs)
