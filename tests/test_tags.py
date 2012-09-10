import os
from pprint import pprint
from subprocess import call
from unittest import TestCase
import itertools

from sgsession import fixtures

from sgfs import SGFS


root = os.path.join(os.path.dirname(__file__), 'root_' + fixtures.timestamp)


def setUpModule():
    fixtures.setup_project()


class TestTags(TestCase):
    
    def setUp(self):
        self.sgfs = SGFS(root=root, shotgun=fixtures.sg)
        self.session = self.sgfs.session
        
    def test_set_get(self):
        
        path = os.path.join(root, 'tags', 'basics')
        os.makedirs(path)
        print path
        
        dummy = self.session.merge({
            'type': 'Shot',
            'id': 123,
            'code': 'DM_001',
            'sg_sequence': {
                'type': 'Sequence',
                'id': 234,
                'code': 'DM',
                'project': {
                    'type': 'Project',
                    'name': 'A dummy project',
                    'id': 345,
                }
            }, 'project': {
                'type': 'Project',
                'id': 345,
            }
        })
        self.sgfs.tag_directory_with_entity(path, dummy)
        
        tags = self.sgfs.get_directory_tags(path)
        pprint(tags)
        
        self.assert_(False)
    
