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
        
        self.sgfs.tag_directory_with_entity(path, entity, cache=False)
        
        new_sgfs = SGFS(root=self.sandbox, session=Session(self.sg))
        tags = new_sgfs.get_directory_entity_tags(path)
        tags[0]['entity'].pprint()
        self.assertEqual(1, len(tags))
        print
        
        self.assertSameEntity(shot, tags[0].get('entity'))
        self.assertSameEntity(seq, tags[0]['entity'].get('sg_sequence'))
        self.assertSameEntity(proj, tags[0]['entity'].get('project'))
        self.assertSameEntity(proj, tags[0]['entity']['sg_sequence'].get('project'))
        
        self.assertIsNotNone(tags[0]['entity'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['project'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['sg_sequence'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['sg_sequence']['project'].get('updated_at'))
        
        entity2 = self.session.merge(seq.Shot('AA_002'))
        self.session.fetch_core(entity2.fetch_heirarchy())
        entity2.pprint()
        print
        
        self.sgfs.tag_directory_with_entity(path, entity2, cache=False)
        
        new_sgfs = SGFS(root=self.sandbox, session=Session(self.sg))
        tags = new_sgfs.get_directory_entity_tags(path)
        self.assertEqual(2, len(tags))
        tags[0]['entity'].pprint()
        tags[1]['entity'].pprint()
        print
        
        self.assertSameEntity(shot, tags[0].get('entity'))
        self.assertSameEntity(seq, tags[0]['entity'].get('sg_sequence'))
        self.assertSameEntity(proj, tags[0]['entity'].get('project'))
        self.assertSameEntity(proj, tags[0]['entity']['sg_sequence'].get('project'))
        
        self.assertIsNotNone(tags[0]['entity'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['project'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['sg_sequence'].get('updated_at'))
        self.assertIsNotNone(tags[0]['entity']['sg_sequence']['project'].get('updated_at'))
        
        self.assertSameEntity(entity2, tags[1].get('entity'))
        self.assertSameEntity(seq, tags[1]['entity'].get('sg_sequence'))
        self.assertSameEntity(proj, tags[1]['entity'].get('project'))
        self.assertSameEntity(proj, tags[1]['entity']['sg_sequence'].get('project'))
        
        self.assertIsNotNone(tags[1]['entity'].get('updated_at'))
        self.assertIsNotNone(tags[1]['entity']['project'].get('updated_at'))
        self.assertIsNotNone(tags[1]['entity']['sg_sequence'].get('updated_at'))
        self.assertIsNotNone(tags[1]['entity']['sg_sequence']['project'].get('updated_at'))
        
        