from subprocess import call, list2cmdline
import os


class Processor(object):
    
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.made_directories = set()
        self.touched_files = set()
        self.copied_files = set()
        self.log_events = []
    
    def log(self, msg):
        self.log_events.append(msg)
        if self.verbose:
            print msg
        
    def comment(self, msg):
        for x in msg.splitlines():
            self.log('# ' + x.rstrip())

    def call(self, args):
        self.log(list2cmdline(args))
        if not self.dry_run:
            call(args)
    
    def mkdir(self, path):
        if path not in self.made_directories:
            self.made_directories.add(path)
            self.call(['mkdir', '-p', path])
    
    def touch(self, path):
        if path not in self.touched_files:
            self.touched_files.add(path)
            self.call(['touch', path])
    
    def copy(self, source, dest):
        if dest not in self.copied_files:
            self.copied_files.add(dest)
            self.call(['cp', '-np', source, dest])


