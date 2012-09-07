from pprint import pprint
from unittest import TestCase as BaseTestCase

import shotgun_api3_registry

from sgfs import SGFS
from sgfs.shotgun import Session, Entity

from . import fixtures


def setUpModule():
    fixtures.setup_tasks()
    globals().update(fixtures.__dict__)
    

class TestCase(BaseTestCase):

    def setUp(self):
        self.session = Session(sg)


class TestEntityMerge(TestCase):

    def test_setitem(self):
        a = self.session.merge(a=1)
        a['child'] = dict(b=2)
        self.assertEqual(a['child']['b'], 2)
        self.assert_(isinstance(a['child'], Entity))
    
    def test_setdefault(self):
        a = self.session.merge(a=1)
        a.setdefault('child', dict(b=2))
        self.assertEqual(a['child']['b'], 2)
        self.assert_(isinstance(a['child'], Entity))
    
    def test_recursive_update(self):
        a = self.session.merge(a=1, child=dict(type='Sequence'))
        self.assert_(isinstance(a, Entity))
        self.assert_(isinstance(a['child'], Entity))
        
    def test_simple_update(self):
        a = self.session.merge(a=1)
        b = self.session.merge(b=2)
        a.update(b)
        self.assertEqual(a, self.session.merge(a=1, b=2))
    
    def test_complex_update(self):
        a = self.session.merge(sequence=dict(x=0, a=1))
        b = self.session.merge(sequence=dict(x=3, b=2))
        a.update(b)
        self.assertEqual(a, self.session.merge(sequence=dict(a=1, b=2, x=3)))
    
    
class TestEntityFetch(TestCase):
    
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
        self.assert_(shot['project']['sg_description'])
        
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
        

class TestHeirarchy(TestCase):
    
    def test_fetch_shot_heirarchy(self):
        
        shots = [self.session.merge(x) for x in fixtures.shots]
        self.session.fetch_heirarchy(shots)
        
        for x in shots:
            x.pprint()
            print
        
        self.assertEqual(shots[0].parent()['id'], sequences[0]['id'])
        self.assertEqual(shots[1].parent()['id'], sequences[0]['id'])
        self.assertEqual(shots[2].parent()['id'], sequences[1]['id'])
        self.assertEqual(shots[3].parent()['id'], sequences[1]['id'])
        
        for shot in shots[1:]:
            self.assert_(shot.parent().parent() is shots[0].parent().parent())
        
        self.assert_(shots[0].parent() is shots[1].parent())
        self.assert_(shots[0].parent() is not shots[2].parent())
        self.assert_(shots[2].parent() is shots[3].parent())
        
    # def test_fetch_task_heirarchy(self):
    #     
    #     tasks = [self.session.merge(x) for x in fixtures.tasks]
    #     for x in tasks:
    #         x.pprint()
    #         print
    #     
    #     self.session.fetch_heirarchy(tasks)
    #     for x in tasks:
    #         x.pprint()
    #         print
        
        
        
        