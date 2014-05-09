from subprocess import call
import collections
import errno
import os
import sqlite3

from sgsession import Entity


class PathCache(collections.MutableMapping):
    
    def __init__(self, sgfs, project_root):
        
        self.sgfs = sgfs
        self.project_root = os.path.abspath(project_root)
        
        # We are in the middle of a transtion of where the SQLite file
        # is located, and for now we prioritize the old location.
        for name in ('.sgfs-cache.sqlite', '.sgfs/cache.sqlite'):
            db_path = os.path.join(project_root, name)
            if os.path.exists(db_path):
                break
        else:
            # If it doesn't exist then touch it with read/write permissions for all.
            db_dir = os.path.dirname(db_path)
            umask = os.umask(0)
            try:
                try:
                    os.makedirs(db_dir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                os.umask(0111)
                call(['touch', db_path])
            finally:
                os.umask(umask)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.text_factory = str
        
        with self.conn:
            self.conn.execute('CREATE TABLE IF NOT EXISTS entity_paths (entity_type TEXT, entity_id INTEGER, path TEXT)')
            self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS entity_paths_entity ON entity_paths(entity_type, entity_id)')
    
    def __repr__(self):
        return '<%s for %r at 0x%x>' % (self.__class__.__name__, self.project_root, id(self))
    
    def __setitem__(self, entity, path):
        
        if not isinstance(entity, Entity):
            raise TypeError('path cache keys must be entities; got %r %r' % (type(entity), entity))
        if not isinstance(path, basestring):
            raise TypeError('path cache values must be basestring; got %r %r' % (type(path), path))
        
        path = os.path.relpath(os.path.abspath(path), self.project_root)
        
        with self.conn:
            self.conn.execute('INSERT OR REPLACE into entity_paths values (?, ?, ?)', (entity['type'], entity['id'], path))
    
    def __getitem__(self, entity):
        if not isinstance(entity, Entity):
            raise TypeError('path cache keys must be entities; got %r %r' % (type(entity), entity))
        with self.conn:
            c = self.conn.cursor()
            c.execute('SELECT path FROM entity_paths WHERE entity_type = ? AND entity_id = ?', (entity['type'], entity['id']))
            row = c.fetchone()
            if row is None:
                raise KeyError(entity)
            path = os.path.abspath(os.path.join(self.project_root, row[0]))
            if any(tag['entity'] is entity for tag in self.sgfs.get_directory_entity_tags(path)):
                return path
            else:
                raise KeyError(entity)
    
    def __delitem__(self, entity):
        if not isinstance(entity, Entity):
            raise TypeError('path cache keys must be entities; got %r %r' % (type(entity), entity))
        with self.conn:
            self.conn.execute('DELETE FROM entity_paths WHERE entity_type = ? AND entity_id = ?', (entity['type'], entity['id']))
    
    def __len__(self):
        with self.conn:
            c = self.conn.cursor()
            return c.execute('SELECT COUNT(1) FROM entity_paths').fetchone()[0]
    
    def __iter__(self):
        with self.conn:
            c = self.conn.cursor()
            for row in c.execute('SELECT entity_type, entity_id FROM entity_paths'):
                yield self.sgfs.session.merge(dict(type=row[0], id=row[1]))
    
    def walk_directory(self, path, entity_type=None, must_exist=True):
        relative = os.path.relpath(path, self.project_root)
        
        # Special case the Projects.
        if relative == '.':
            relative = ''
            
        if relative.startswith('.'):
            raise ValueError('path not in project; %r' % path)
        
        with self.conn:

            c = self.conn.cursor()
            if entity_type is not None:
                c.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE entity_type = ? AND path LIKE ?', (entity_type, relative + '%'))
            else:
                c.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE path LIKE ?', (relative + '%', ))
            
            for row in c:
                entity = self.sgfs.session.merge(dict(type=row[0], id=row[1]))
                path = os.path.join(self.project_root, row[2])
                if must_exist and not os.path.exists(path):
                    continue
                yield path, entity

