"""

This is lifted directly out of the WesternX key_base repo. Please be very
careful in changing this until our tools have migrated.

Asset scene paths look like:
    {workspace}/{directory}/v{version}/{sub_directory}/{entity}_step_name_{detail}_v{version}{ext}
    {workspace}/{directory}/v{version}/revisions/{sub_directory}/{entity}_step_name_{detail}_v{version}_r{revision}{ext}

Note the versioning information between `directory` and `sub_directory`.

Everything else looks like:
    {workspace}/{directory}/{sub_directory}/{entity}_step_name_{detail}_v{version}_r{revision}{ext}

TODO:
    - Use SGFS to determine where the workspace is (by looking for a directory
      tagged with a Task).

"""

import os
import re


class SceneName(object):

    def __init__(self, **kwargs):
        
        # Reasonable defaults.
        self.detail = ''
        self.entity_name = ''
        self.entity_type = None
        self.extension = ''
        self.revision = 1
        self.step_name = kwargs.get('step_name')
        self.sub_directory = ''
        self.directory = 'scenes'
        self.version = 1
        
        # Callbacks.
        self.warning = kwargs.pop('warning', self.warning)
        self.error = kwargs.pop('error', self.error)
        if self.error is False:
            self.error = self.warning
        
        # Parse given paths.
        self.workspace = kwargs.pop('workspace', None)
        if self.workspace is not None:
            self._parse_workspace(self.workspace)
        self.filename = kwargs.pop('filename', None)
        if self.filename is not None:
            self._parse_filename(self.filename)
        
        # Set kwargs.
        self.detail = kwargs.pop('detail', self.detail)
        self.entity_name = kwargs.pop('entity_name', self.entity_name)
        self.entity_type = kwargs.pop('entity_type', self.entity_type)
        self.extension = kwargs.pop('extension', self.extension)
        self.revision = int(kwargs.pop('revision', self.revision))
        self.step_name = kwargs.pop('step_name', self.step_name)
        # "scenes_name" one is for backwards compatibility.
        self.directory = kwargs.pop('directory', kwargs.pop('scenes_name', self.directory))
        self.sub_directory = kwargs.pop('sub_directory', self.sub_directory)
        self.version = int(kwargs.pop('version', self.version))
        
        self._step_names = []
        
        if kwargs:
            raise TypeError(
                ('%s recieved too many kwargs: ' % self.__class__.__name__) +
                ', '.join(kwargs)
            )
    
    def __repr__(self):
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))
    
    def __str__(self):
        return self.get_path()
    
    def warning(self, message):
        print '# Warning:', message
    
    def error(self, message):
        raise ValueError(message)

    def _split_workspace(self, workspace):

        # Isolate the entity from the standard WesternX structure, e.g.:
        # - /Volumes/VFX/Projects/Super_Buddies/Assets/Character/Cow
        # - /Volumes/VFX/Projects/Testing_Sandbox/SEQ/GP/GP_001_001
        m = re.match(r'(/.+?)/(SEQ|Assets)/([^/]+)/([^/]+)/([^/]+)(?:/(maya|nuke))?', workspace)
        return m, workspace[m.end(0):].strip('/') if m else workspace

    def _parse_workspace(self, workspace, warn_on_remaining=True):
        
        m, remaining = self._split_workspace(workspace)

        if not m:
            self.error('Could not parse WesternX workspace.')
            return

        if remaining and warn_on_remaining:
            self.warning('workspace may be too specific; %r remains' % remaining)
        
        filename_dir, parent_type, parent_name, self.entity_name, self.step_name, software = m.groups()
        self.entity_type = 'Shot' if parent_type == 'SEQ' else 'Asset'
        self.workspace = m.group(0)
        
    
    def _parse_filename(self, filename):
        
        if os.path.isabs(filename):
            rel_filename = os.path.relpath(filename, self.workspace)
            if rel_filename.startswith('.'):
                self.warning('file not in workspace; %r not in %r' % (filename, self.workspace))
                _, rel_filename = self._split_workspace(filename)
        else:
            rel_filename = filename

        # Extension
        filename, self.extension = os.path.splitext(rel_filename)
        
        directory = os.path.dirname(filename)
        filename = os.path.basename(filename)
        
        # Versions and revisions come out of the basename, and then the dirname
        m = re.search(r'v(\d+)', filename) or re.search(r'v(\d+)', directory)
        if m:
            self.version = int(m.group(1))
        else:
            self.warning('Could not match version.')
        m = re.search(r'r(\d+)', filename) or re.search(r'r(\d+)', directory)
        if m:
            self.revision = int(m.group(1))
        else:
            self.revision = 0
        
        # Completely strip versioning out of the basename.
        filename = re.sub(r'_?[rv]\d+/?', '', filename)
        
        # Assign (sub)directory around versioning.
        directory_parts = re.split(r'v\d+(?:/revisions?)?(?:/|$)', directory)
        if len(directory_parts) > 1:
            self.directory, self.sub_directory = directory_parts
        else:
            self.directory = directory
        
        # Strip entity name.
        if self.entity_name and filename.lower().startswith(self.entity_name.lower()):
            filename = filename[len(self.entity_name):].lstrip('_')
        else:
            self.warning('Could not find shot/asset name prefix.')
        
        # Strip step name.
        if self.step_name and filename.lower().startswith(self.step_name.lower()):
            filename = filename[len(self.step_name):].lstrip('_')
        else:
            self.warning('Could not find task/step prefix.')
            
        self.detail = filename.strip('_')
    
    def get_step_names(self):
        
        if self._step_names:
            return self._step_names
        
        step_dir = os.path.dirname(os.path.dirname(self.workspace))
        try:
            for name in os.listdir(step_dir):
                # XXX: Hardcoded SGFS tag name?!
                if os.path.exists(os.path.join(step_dir, name, '.sgfs.yml')):
                    self._step_names.append(name)
        except OSError:
            pass
        
        # Make sure we have a step name.
        if self.step_name is None:
            if not self._step_names:
                self.error('Could not identify pipeline step.')
                self._step_names = ['']
            self.step_name = self._step_names[0]
        
        # Make sure the step name is in step_names.
        self._step_names.append(self.step_name)
        self._step_names = sorted(set(self._step_names), key=lambda x: x.lower())
        
        return self._step_names
    
    def get_basename(self):
        parts = [
            self.entity_name,
            self.step_name,
            self.detail,
            'v%04d' % self.version,
            'r%04d' % self.revision if self.revision else None,
        ]
        basename = '_'.join(x.strip() for x in parts if x)
        basename = re.sub(r'[^a-zA-Z0-9]+', '_', basename)
        basename = basename.strip('_')
        return basename + self.extension
    
    def get_directory(self):
        
        path = os.path.join(self.workspace, self.directory)
            
        # Add '/v0001/revisions' if in an Asset and this is a maya scene.
        # Because the artists said so. That's why.
        if self.entity_type == 'Asset' and self.directory.startswith('scenes'):
            path = os.path.join(path, 'v' + '%04d' % self.version)
            if self.revision:
                path = os.path.join(path, 'revisions')
                
        path = os.path.join(path, self.sub_directory)
        return path
    
    def get_path(self):
        return os.path.join(self.get_directory(), self.get_basename())

