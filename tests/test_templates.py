from common import *


class TestBareTemplates(TestCase):
    
    def assertTemplateFormat(self, format, output, **data):
        tpl = Template(format)
        value = tpl.format(**data)
        self.assertEqual(value, output)
    
    def assertTemplateMatch(self, format, input, **data):
        tpl = Template(format)
        m = tpl.match(input)
        self.assertEqual(m, data)
    
    def assertTemplateRoundtrip(self, format, final, **data):
        tpl = Template(format)
        out = tpl.format(**data)
        self.assertEqual(out, final)
        out = tpl.match(final)
        self.assertEqual(out, data)
        
    def test_defaults(self):
        self.assertTemplateRoundtrip('A-{x:s}-Z', 'A-123-Z', x='123')
        self.assertTemplateRoundtrip('A-{x}-Z', 'A-123-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:s}-Z', 'A-1.23-Z', x='1.23')
        self.assertTemplateRoundtrip('A-{x}-Z', 'A-1.23-Z', x=1.23)
        self.assertTemplateMatch('A-{x}-Z', 'A-0x123-Z', x=0x123)
        self.assertTemplateMatch('A-{x}-Z', 'A-0o123-Z', x=0o123)
        self.assertTemplateMatch('A-{x}-Z', 'A-0b111-Z', x=0b111)
    
    def test_integers(self):
        self.assertTemplateRoundtrip('A-{x}-Z', 'A-123-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:d}-Z', 'A-123-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:04d}-Z', 'A-0123-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:x}-Z', 'A-7b-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:#x}-Z', 'A-0x7b-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:X}-Z', 'A-7B-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:#X}-Z', 'A-0X7B-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:o}-Z', 'A-173-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:#o}-Z', 'A-0o173-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:b}-Z', 'A-1111011-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:#b}-Z', 'A-0b1111011-Z', x=123)
        self.assertTemplateRoundtrip('A-{x:n}-Z', 'A-123-Z', x=123)
        
    def test_deep_structure(self):
        tpl = Template('{task[step][name]}_v{version:04d}_r{revision:04d}{ext}')
        data = dict(task=dict(step=dict(name="Anim")), version=2, revision=8, ext='.mb')
        out = tpl.format(**data)
        self.assertEqual(out, 'Anim_v0002_r0008.mb')
        self.assertEqual(tpl.match(out), data)

class TestBoundTemplates(TestCase):
    
    def mock_structure(self, path, namespace=None):
        context = Mock()
        context.build_eval_namespace.return_value = namespace or {}
        structure = Mock(path=path, context=context)
        return structure
        
    def test_format(self):
        structure = self.mock_structure(
            path='/path/to/shot',
            namespace={'basename': 'Awesome_Shot', 'ext': '.mb'},
        )
        tpl = BoundTemplate('{basename}_v{version:04d}{ext}', structure)
        self.assertEqual(
            tpl.format(version=123, ext='.ma'),
            '/path/to/shot/Awesome_Shot_v0123.ma',
        )
    
    def test_match(self):
        structure = self.mock_structure(
            path='/path/to/shot',
        )
        tpl = BoundTemplate('{basename}_v{version:04d}{ext}', structure)
        self.assertEqual(
            tpl.match('/path/to/shot/Awesome_Shot_v0123.ma'),
            {'basename': 'Awesome_Shot', 'version': 123, 'ext': '.ma'},
        )
    
    
    
class TestSGFSTemplates(TestCase):
    
    def setUp(self):
        sg = Shotgun()
        self.sg = self.fix = fix = Fixture(sg)
        
        self.proj_name = 'Test Project ' + mini_uuid()
        proj = fix.Project(self.proj_name)
        seqs = [proj.Sequence(code, project=proj) for code in ('AA', )]#, 'BB')]
        shots = [seq.Shot('%s_%03d' % (seq['code'], i), project=proj) for seq in seqs for i in range(1, 2)]
        steps = [fix.find_or_create('Step', code=code, short_name=code) for code in ('Anm', )] # 'Comp', 'Light', 'Model')]
        # assets = [proj.Asset(sg_asset_type=type_, code="%s %d" % (type_, i)) for type_ in ('Character', 'Vehicle') for i in range(1, 3)]
        assets = []
        tasks = [entity.Task(step['code'] + ' something', step=step, entity=entity, project=proj) for step in (steps + steps[-1:]) for entity in (shots + assets)]
        
        self.proj = minimal(proj)
        self.seqs = map(minimal, seqs)
        self.shots = map(minimal, shots)
        self.steps = map(minimal, steps)
        self.tasks = map(minimal, tasks)
        # self.assets = map(minimal, assets)

        self.session = Session(self.sg)
        self.sgfs = SGFS(root=self.sandbox, session=self.session, schema_name='testing')
        self = None
    
    def test_shot_workspace(self):

        self.sgfs.create_structure(self.tasks, allow_project=True)
        
        tpl = self.sgfs.find_template(self.tasks[0], 'maya_scene')
        self.assertIsInstance(tpl, BoundTemplate)
        self.assertTrue(tpl.path.endswith('AA_001/Anm/maya'), tpl.path)
        path = tpl.format(name="Bouncing_Ball", version=1, ext=".mb")
        self.assertEqual(os.path.join(tpl.path, 'scenes/AA_001_Bouncing_Ball_v0001.mb'), path)
        
        res = self.sgfs.template_from_path(path, 'maya_scene')
        self.assertIsNotNone(res)
        tpl, m = res
        self.assertEqual(m.get('version'), 1)
        # CANT TEST FOR NAME HERE, since it will match wrong.
        
        # self.fail()

    def test_definition_patterns(self):

        tpl = self.sgfs.find_template(self.tasks[0], 'maya_camera_folder')
        self.assertEqual(tpl.template.format(), 'data/camera')

        tpl = self.sgfs.find_template(self.tasks[0], 'maya_lightrig_folder')
        self.assertEqual(tpl.template.format(), 'data/generic')


        
        
        