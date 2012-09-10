import os
from subprocess import call, list2cmdline


class Processor(object):
    
    def __init__(self, schema, project):
        self.schema = schema
        self.project = project
    
    def join_to_schema(self, path):
        return os.path.join(self.schema, path)
    
    def join_to_project(self, path):
        return os.path.join(self.project, path)
    
    def call(self, args):
        call(args)
    
    def mkdir(self, path):
        self.call(['mkdir', '-p', self.join_to_project(path)])
    
    def touch(self, path):
        self.call(['touch', self.join_to_project(path)])
    
    def copy(self, source, dest):
        self.call(['cp', '-p', self.join_to_schema(source), self.join_to_project(dest)])


class Previewer(Processor):
    
    def __init__(self, *args, **kwargs):
        super(Previewer, self).__init__(*args, **kwargs)
        self.made_dirs = set()
    
    def mkdir(self, path):
        if path in self.made_dirs:
            return
        self.made_dirs.add(path)
        return super(Previewer, self).mkdir(path)
    
    def call(self, args):
        print list2cmdline(args)
