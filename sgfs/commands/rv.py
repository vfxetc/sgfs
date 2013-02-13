import os
from subprocess import call, Popen, PIPE
import sys

from . import Command
from . import utils


class OpenSequenceInRV(Command):
    """%prog [options] [paths]
    
    Open the latest version for each given entity.
    
    """
        
    def run(self, sgfs, opts, args):
        
        # Parse them all.
        arg_to_movie = {}
        arg_to_entity = {}

        for arg in args:

            if os.path.exists(arg):
                arg_to_movie[arg] = arg
                continue

            print 'Parsing %r...' % arg

            data = utils.parse_spec(sgfs, arg.split(), ['Shot'])
            type_ = data.get('type')
            id_ = data.get('id')
            if not (type_ or id_):
                print 'no entities found for', repr(arg)
                return 1

            arg_to_entity.setdefault(type_, {})[arg] = sgfs.session.merge(dict(type=type_, id=id_))

        tasks = arg_to_entity.pop('Task', {})
        shots = arg_to_entity.pop('Shot', {})
        if arg_to_entity:
            print 'found entities that were not Task or Shot:', ', '.join(sorted(arg_to_entity))
            return 2

        if tasks:
            print 'Getting shots from tasks...'
            sgfs.session.fetch(tasks.values(), 'entity')
            for arg, task in tasks.iteritems():
                shots[arg] = task['entity']

        if shots:
            print 'Getting versions from shots...'
            sgfs.session.fetch(shots.values(), ('sg_latest_version.Version.sg_path_to_movie', 'sg_latest_version.Version.sg_path_to_frames'))
            for arg, shot in shots.iteritems():

                version = shot.get('sg_latest_version')
                if not version:
                    print 'no version for', shot
                    return 3

                path = version.get('sg_path_to_movie') or version.get('sg_path_to_frames')
                if not path:
                    print 'no movie or frames for', version
                    return 4

                arg_to_movie[arg] = path

        movies = [arg_to_movie[arg] for arg in args]
        print 'Opening:'
        print '\t' + '\n\t'.join(movies)

        rvlink = Popen(['rv', '-bakeURL'] + movies, stderr=PIPE).communicate()[1].strip().split()[-1]
        self.open(rvlink)
    
    def open(self, x):
        if sys.platform.startswith('darwin'):
            call(['open', x])
        else:
            call(['xdg-open', x])


run = OpenSequenceInRV()

