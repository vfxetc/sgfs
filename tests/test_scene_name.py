import os
from unittest import TestCase

from sgfs.ui.scene_name import SceneName


root = '/Projects/Test_Project'

# Entity Folders
shot = os.path.join(root, 'SEQ/AA/AA_001_001')
asset = os.path.join(root, 'Assets/Characters/Cow')


workspaces = {
    'nuke': os.path.join(shot, 'Comp/nuke'),
    'sgfs_asset': os.path.join(root, 'Assets/Character/Cow/Light/maya'),
    'sgfs_shot': os.path.join(root, 'SEQ/GP/GP_001_001/Light/maya'),
}

cases = {
    
    'nuke_script': 'scripts/AA_001_001_Comp_v0001.nk',
    
    'sgfs_asset': 'scenes/v0001/Cow_Light_v0001.mb',
    'sgfs_asset_rev': 'scenes/v0001/revisions/Cow_Light_v0001_r0002.mb',
    'sgfs_asset_subdir': 'scenes/v0001/light_rig/Cow_Light_v0001.mb',
    'sgfs_asset_extdir': 'scenes/light_rig/v0001/Cow_Light_v0001.mb',
    'sgfs_asset_subdir_rev': 'scenes/v0001/revisions/light_rig/Cow_Light_v0001_r0001.mb',
    
    'sgfs_shot': 'scenes/GP_001_001_Light_v0001.mb',
    'sgfs_shot_rev': 'scenes/GP_001_001_Light_v0001_r0002.mb',
    'sgfs_shot_subdir': 'scenes/light_rig/GP_001_001_Light_v0001_r0001.mb',
    
    'sgfs_shot_detail': 'scenes/GP_001_001_Light_Detail_v0001.mb',
    'sgfs_shot_rev_detail': 'scenes/GP_001_001_Light_Detail_v0001_r0002.mb',
    'sgfs_shot_subdir_detail': 'scenes/pre_track/GP_001_001_Light_Detail_v0001_r0001.mb',
}


class TestRoundTrip(TestCase):
    
    @classmethod
    def add_roundtrip(cls, name, workspace, filename):
        def tester(self):
            self.check_roundtrip(workspace, filename)
        tester.__name__ = 'test_roundtrip_' + name
        setattr(cls, tester.__name__, tester)
        
    def check_roundtrip(self, workspace, filename):
        scene_name = SceneName(workspace=workspace, filename=filename)
        generated = scene_name.get_path()
        print 'ORIGINAL:', repr(filename)
        print 'GENERATE:', repr(generated)
        self.assertEqual(filename, generated)

    def test_project_not_in_workspace(self):
        self.assertRaises(ValueError, SceneName, workspace='/path/to/workspace', filename='/path/to/project')

for name, filename in cases.iteritems():
    for ws_name, workspace in workspaces.iteritems():
        if name.startswith(ws_name):
            break
    else:
        raise ValueError('no workspace for ' + name)
    TestRoundTrip.add_roundtrip(name, workspace, os.path.join(workspace, filename))


        