from pprint import pprint
from unittest import TestCase as BaseTestCase

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.shotgun import Session, Entity


def setUpModule():
    from . import fixtures
    fixtures.setup_project()
    globals().update(fixtures.__dict__)
    

class TestCase(BaseTestCase):
    pass


class TestEntityMerge(TestCase):
    

    def setUp(self):
        self.session = Session()
    
    def test_recursive_entity(self):
        a = self.session.as_entity(a=1, child=dict(type='Sequence'))
        self.assert_(isinstance(a, Entity))
        self.assert_(isinstance(a['child'], Entity))
        
    def test_simple_merge(self):
        a = self.session.as_entity(a=1)
        b = self.session.as_entity(b=2)
        a.update(b)
        self.assertEqual(a, self.session.as_entity(a=1, b=2))
    
    def test_complex_merge(self):
        a = self.session.as_entity(sequence=dict(x=0, a=1))
        b = self.session.as_entity(sequence=dict(x=3, b=2))
        a.update(b)
        self.assertEqual(a, self.session.as_entity(sequence=dict(a=1, b=2, x=3)))
    
    
class TestEntityFetch(TestCase):
    
    def setUp(self):
        self.session = Session(sg)
    
    @classmethod
    def setUpClass(cls):
        cls.seq = sg.create('Sequence', dict(code=cls.__name__ + '.seq', project=project))
        cls.shot = sg.create('Shot', dict(code=cls.__name__ + '.shot', sg_sequence=cls.seq, project=project))
        
    def test_fetch_scalar(self):
        shot = self.session.find_one('Shot', [
            ('code', 'is', self.shot['code']),
            ('project', 'is', {'type': 'Project', 'id': project['id']}),
        ])
        self.assert_('description' not in shot)
        shot.fetch(['code', 'description', 'created_at', 'does_not_exist'])
        self.assertEqual(shot['code'], self.shot['code'])
        self.assertEqual(shot['description'], None)
        self.assert_(shot['created_at'])
        self.assert_('does_not_exist' not in shot)
    
    def test_fetch_entity(self):
        
        shot = self.session.find_one('Shot', [
            ('code', 'is', self.shot['code']),
            ('project', 'is', {'type': 'Project', 'id': project['id']}),
        ])
        
        self.assert_('project' not in shot)
        
        shot.fetch(['project'])
        self.assertEqual(shot['project']['id'], project['id'])
        
        shot['project'].fetch(['sg_description'])
        self.assertEqual(shot['project']['sg_description'], project['sg_description'])
        
        project_entity = self.session.find_one('Project', [
            ('id', 'is', project['id']),
        ])
        self.assert_(project_entity is shot['project'])
    
    def test_parents(self):
        
        shot = self.session.find_one('Shot', [
            ('code', 'is', self.shot['code']),
            ('project', 'is', {'type': 'Project', 'id': project['id']}),
        ])
        
        self.assert_('sg_sequence' not in shot)
        
        seq = shot.parent()
        self.assertEqual(seq['id'], self.seq['id'])
        
        proj = seq.parent()
        self.assertEqual(proj['id'], project['id'])
        
        shot.fetch(['project'])
        self.assert_(shot['project'] is proj)
        
        
    