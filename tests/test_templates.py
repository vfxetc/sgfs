from common import *


class TestTemplates(TestCase):
    
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

    