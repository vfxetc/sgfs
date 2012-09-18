from subprocess import call, list2cmdline
import os


class Processor(object):
    
    def __init__(self, verbose=False, dry_run=False, allow_project=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.made_directories = set()
        self.touched_files = set()
        self.copied_files = set()
        self.log_events = []
        self.disallowed_entities = set()
        if not allow_project:
            self.disallowed_entities.add('Project')
    
    def assert_allow_entity(self, entity):
        if entity['type'] in self.disallowed_entities:
            raise ValueError('Not allowed to create %s %d' % (entity['type'], entity['id']))
        
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
            self.log(list2cmdline(['mkdir', '-pm', '0777', path]))
            if not self.dry_run:
                # Race condition?
                umask = os.umask(0)
                os.makedirs(path, 0777)
                os.umask(umask)
    
    def touch(self, path):
        if path not in self.touched_files:
            self.touched_files.add(path)
            self.call(['touch', path])
            if not self.dry_run:
                os.chmod(path, 0666) # Race condition?
    
    def copy(self, source, dest):
        if dest not in self.copied_files:
            self.copied_files.add(dest)
            self.call(['cp', '-np', source, dest])
            if not self.dry_run:
                os.chmod(dest, 0666) # Race condition?


