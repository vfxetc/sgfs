from pprint import pprint
from unittest import TestCase

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.shotgun import Session, Entity


class TestEntity(TestCase):
    
    def test_simple_merge(self):
        session = Session()
        a = session.as_entity(dict(a=1))
        b = session.as_entity(dict(b=2))
        a.merge(b)
        self.assertEqual(a, session.as_entity(dict(a=1, b=2)))
    
    def test_complex_merge(self):
        session = Session()
        a = session.as_entity(dict(sequence=dict(x=0, a=1)))
        b = session.as_entity(dict(sequence=dict(x=3, b=2)))
        a.merge(b)
        self.assertEqual(a, session.as_entity(dict(sequence=dict(a=1, b=2, x=3))))
    
    
    