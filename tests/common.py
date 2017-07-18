from pprint import pprint, pformat
import collections
import datetime
import errno
import itertools
import logging
import os
import sys

from mock import Mock

from sgfs import SGFS, Schema, Context, Structure, Template, BoundTemplate
from sgmock import Fixture, TestCase as BaseTestCase
from sgsession import Session, Entity


_shotgun_server = os.environ.get('SHOTGUN', 'mock')
if _shotgun_server == 'mock':
    from sgmock import Shotgun, ShotgunError, Fault
else:
    from shotgun_api3 import ShotgunError, Fault
    import shotgun_api3_registry
    def Shotgun():
        return shotgun_api3_registry.connect('sgsession.tests', server=_shotgun_server)


if sys.version_info < (2, 6):
    def next(iter_, *args):
        try:
            return iter_.next()
        except StopIteration:
            if args:
                return args[0]
            else:
                raise


# Force some defaults for testing.
os.environ['SGFS_SCHEMA'] = 'testing'
os.environ.pop('SGFS_CACHE', None)


def mini_uuid():
    return os.urandom(4).encode('hex')

def timestamp():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

def minimal(entity):
    return dict(type=entity['type'], id=entity['id'])

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


if os.path.abspath(os.path.join(__file__, '..', '..')) == os.path.abspath('.'):
    sandbox = './sandbox'
else:
    sandbox = os.path.abspath(os.path.join(__file__, '..', '..', 'sandbox'))
sandbox = os.path.join(sandbox, datetime.datetime.now().isoformat('T'))
makedirs(sandbox)


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
        makedirs(path)
        return path

    def SGFS(self, **kwargs):
        kwargs.setdefault('root', self.sandbox)
        kwargs.setdefault('session', self.session)
        return SGFS(**kwargs)

    def setUp(self):
        self.shotgun = Shotgun()
        self.fixture = Fixture(self.shotgun)
        self.session = Session(self.shotgun)
        self.sgfs = self.SGFS()


class LogCapturer(logging.Handler, collections.Sequence):

    def __init__(self, name=None, silent=False):
        super(LogCapturer, self).__init__()
        self.logger_name = name
        self.silence_others = silent
        self.records = []

    def __enter__(self):
        self.logger = logging.getLogger(self.logger_name)
        if self.silence_others:
            self.existing_handlers = self.logger.handlers[:]
            self.logger.handlers[:] = []
        self.logger.addHandler(self)
        return self

    def __exit__(self, *args):
        if self.silence_others:
            self.logger.handlers[:] = self.existing_handlers
        else:
            self.logger.removeHandler(self)

    def emit(self, record):
        self.records.append(record)

    def __getitem__(self, i):
        return self.records[i]

    def __len__(self):
        return len(self.records)

capture_logs = LogCapturer

