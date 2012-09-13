from common import *


class TestTags(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session)
        
    def test_set_get(self):
        
        path = os.path.join(self.sandbox, 'test_set_get')
        os.makedirs(path)
        
        proj = self.fix.Project(self.project_name())
        seq = proj.Sequence('AA')
        shot = seq.Shot('AA_001')
        
        entity = self.session.merge(shot)
        self.session.fetch_core(entity.fetch_heirarchy())
        entity.pprint()
        print
        
        self.sgfs.tag_directory_with_entity(path, entity)
        
        new_sgfs = SGFS(root=self.sandbox, session=Session(self.sg))
        tags = new_sgfs.get_directory_tags(path)
        tags[0]['entity'].pprint()
        print
        
        self.assertEqual(1, len(tags))
        self.assertSameEntity(shot, tags[0].get('entity'))
        self.assertSameEntity(seq, tags[0]['entity'].get('sg_sequence'))
        self.assertSameEntity(proj, tags[0]['entity'].get('project'))
        self.assertSameEntity(proj, tags[0]['entity']['sg_sequence'].get('project'))
        