import argparse
import os

from dirmap import DirMap
from sgsession.utils import parse_isotime

from sgfs import SGFS


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recurse', action='store_true')
    parser.add_argument('-n', '--dry-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count')
    
    parser.add_argument('-t', '--parse-times', action='store_true')
    parser.add_argument('-d', '--dirmap', action='append', dest='_dirmap')

    parser.add_argument('roots', nargs='+')

    cmd = parser.parse_args(namespace=Repair())
    cmd.run()


class Repair(object):

    def __init__(self):
        self._logs = {}
        self.sgfs = SGFS()

    def log(self, message):
        self._logs[message] = self._logs.get(message, 0) + 1

    def run(self):

        self.dirmap = DirMap(self._dirmap) if self._dirmap else None

        for root in self.roots:

            root = os.path.abspath(root)
            if self.recurse:
                for path, _, _ in os.walk(root):
                    self.repair_path(path)
            else:
                self.repair_path(root)

    def repair_path(self, path):

        tags = self.sgfs._read_directory_tags(path)
        if not tags:
            return

        tags = self.repair(tags)

        if self.verbose and (self.verbose > 1 or self._logs):
            print path

        if not self._logs:
            return

        for k, v in sorted(self._logs.items()):
            print '    {}x {}'.format(v, k)

        if not self.dry_run:
            self.sgfs._write_directory_tags(path, tags, replace=True)

    def repair(self, data):

        if isinstance(data, (list, tuple)):
            return [self.repair(x) for x in data]

        if isinstance(data, dict):

            if 'type' in data and 'id' in data:
                self.repair_entity(data)

            # Process the rest of it.
            return {k: self.repair(v) for k, v in data.items()}

        if isinstance(data, basestring) and self.dirmap is not None:
            new = self.dirmap(data)
            if new != data:
                self.log('{} -> {}'.format(data, new))
                return new

        return data

    def repair_entity(self, entity):

        if self.parse_times:
            for key in 'updated_at', 'created_at':
                value = entity.get(key)
                if value and isinstance(value, basestring):
                    entity[key] = parse_isotime(value)
                    self.log('parsed {}[{}].{} == {}'.format(entity['type'], entity['id'], key, entity[key]))

