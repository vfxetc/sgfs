from common import *


class TestTemplates(TestCase):
    
    def test_basic_formatting(self):
        
        template = Template('A_{name}_Z')
        self.assertEqual(template.format(name='123'), 'A_123_Z')

    def test_basic_matching(self):
        
        template = Template('A_{name}_Z')
        m = template.match('A_123_Z')
        self.assertEqual(m, {'name': '123'})
    