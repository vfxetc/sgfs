from pprint import pprint
from subprocess import call
from unittest import TestCase
import datetime
import itertools
import os
import time

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.utils import parent
from sgfs.shotgun import Session, Entity


class TestEntity(TestCase):
    
    def test_simple_merge(self):
        a = Entity(a=1)
        b = Entity(b=2)
        a.merge(b)
        self.assertEqual(a, Entity(a=1, b=2))
    
    def test_complex_merge(self):
        a = Entity(sequence=dict(x=0, a=1))
        b = Entity(sequence=dict(x=3, b=2))
        a.merge(b)
        self.assertEqual(a, Entity(sequence=dict(a=1, b=2, x=3)))
    