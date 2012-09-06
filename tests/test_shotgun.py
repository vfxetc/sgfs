from pprint import pprint
from unittest import TestCase

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.shotgun import Session, Entity


def setUpModule():
    from . import fixtures
    fixtures.setup_project()
    globals().update(fixtures.__dict__)
    

class TestCase(TestCase):
    
    def as_entity(self, x=None, **kwargs):
        x = x or {}
        x.update(kwargs)
        return self.session.as_entity(x)


class TestEntityMerge(TestCase):
    
    def setUp(self):
        self.session = Session()
    
    def test_simple_merge(self):
        a = self.as_entity(dict(a=1))
        b = self.as_entity(dict(b=2))
        a.merge(b)
        self.assertEqual(a, self.as_entity(dict(a=1, b=2)))
    
    def test_complex_merge(self):
        a = self.as_entity(dict(sequence=dict(x=0, a=1)))
        b = self.as_entity(dict(sequence=dict(x=3, b=2)))
        a.merge(b)
        self.assertEqual(a, self.as_entity(dict(sequence=dict(a=1, b=2, x=3))))
    
    
class TestEntityFetch(TestCase):
    
    def setUp(self):
        self.session = Session(sg)
    
    @classmethod
    def setUpClass(cls):
        cls.shot = sg.create('Shot', dict(code=cls.__name__, project=project))
    
    def test_fetch_scalar(self):
        shot = self.session.find_one('Shot', [('code', 'is', self.__class__.__name__)])
        self.assert_('description' not in shot)
        shot.fetch(['code', 'description', 'created_at', 'does_not_exist'])
        self.assertEqual(shot['code'], self.__class__.__name__)
        self.assertEqual(shot['description'], None)
        self.assert_(shot['created_at'])
        self.assert_('does_not_exist' not in shot)
        
        
    