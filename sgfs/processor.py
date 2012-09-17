from subprocess import call, list2cmdline
import os


class Processor(object):
    
    def __init__(self, schema='', project='', verbose=False, dry_run=False):
        self.schema = schema
        self.project = project
        self.verbose = verbose
        self.dry_run = dry_run
        
        self.made_directories = set()
        self.touched_files = set()
        self.copied_files = set()
        
    def comment(self, msg):
        if self.verbose:
            print '\n'.join('# ' + x.rstrip() for x in msg.splitlines())
        
    def join_to_schema(self, path):
        return os.path.join(self.schema, path)
    
    def join_to_project(self, path):
        return os.path.join(self.project, path)
    
    def call(self, args):
        if self.verbose:
            print list2cmdline(args)
        if not self.dry_run:
            call(args)
    
    def mkdir(self, path):
        if path not in self.made_directories:
            self.made_directories.add(path)
            self.call(['mkdir', '-p', self.join_to_project(path)])
    
    def touch(self, path):
        if path not in self.touched_files:
            self.touched_files.add(path)
            self.call(['touch', self.join_to_project(path)])
    
    def copy(self, source, dest):
        if dest not in self.copied_files:
            self.copied_files.add(dest)
            self.call(['cp', '-np', self.join_to_schema(source), self.join_to_project(dest)])


