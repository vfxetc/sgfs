from common import *


class TestParsing(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session)
    
    def test_parsing_paths(self):
        
        proj_fix = self.fix.Project(self.project_name())
        proj = self.session.merge(proj_fix)
        seq = self.session.merge(proj_fix.Sequence('ParseTarget'))

        proj_path = os.path.join(self.sandbox, 'project')
        seq_path = os.path.join(self.sandbox, 'project', 'sequence')
        os.makedirs(seq_path)

        self.sgfs.tag_directory_with_entity(proj_path, proj, cache=False)
        self.sgfs.tag_directory_with_entity(seq_path, seq, cache=False)
        
        self.assertSameEntity(
            self.sgfs.parse_user_input(seq_path),
            seq,
        )

        self.assertSameEntity(
            self.sgfs.parse_user_input(seq_path, entity_types='Project'),
            proj,
        )
