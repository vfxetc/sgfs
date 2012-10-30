from pprint import pprint, pformat
import datetime
import itertools
import os
import sys

from sgmock import Fixture
from sgmock import TestCase as BaseTestCase

_shotgun_server = os.environ.get('SHOTGUN', 'mock')
if _shotgun_server == 'mock':
    from sgmock import Shotgun, ShotgunError, Fault
else:
    from shotgun_api3 import ShotgunError, Fault
    import shotgun_api3_registry
    def Shotgun():
        return shotgun_api3_registry.connect('sgsession.tests', server=_shotgun_server)

from sgsession import Session, Entity

from sgfs import SGFS, Schema, Context, Structure, Template


if sys.version_info < (2, 6):
    def next(iter_, *args):
        try:
            return iter_.next()
        except StopIteration:
            if args:
                return args[0]
            else:
                raise


def mini_uuid():
    return os.urandom(4).encode('hex')

def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

def minimal(entity):
    return dict(type=entity['type'], id=entity['id'])


if os.path.abspath(os.path.join(__file__, '..', '..')) == os.path.abspath('.'):
    sandbox = './sandbox'
else:
    sandbox = os.path.abspath(os.path.join(__file__, '..', '..', 'sandbox'))
sandbox = os.path.join(sandbox, datetime.datetime.now().isoformat('T'))
os.makedirs(sandbox)


class TestCase(BaseTestCase):
    
    @property
    def full_name(self):
        
        try:
            return self._full_name
        except AttributeError:
            pass
        
        module = sys.modules.get(self.__class__.__module__)
        if module and module.__file__:
            file_name = os.path.basename(os.path.splitext(module.__file__)[0])
        else:
            file_name = 'unknown'
        
        self._full_name = file_name + '.' + self.__class__.__name__
        return self._full_name
    
    def project_name(self):
        return 'Test Project - %s - %s' % (self.full_name, mini_uuid())
    
    @property
    def sandbox(self):
        path = os.path.join(sandbox, self.full_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

