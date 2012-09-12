from common import *


class TestTags(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        self.root = os.path.join(sandbox, self.__class__.__name__)
        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.root, session=self.session)
        
    def test_set_get(self):
        
        path = self.root
        if not os.path.exists(path):
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
