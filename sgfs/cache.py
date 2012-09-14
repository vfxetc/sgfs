from __future__ import with_statement

import collections
import os
import sqlite3

from sgsession import Entity


class PathCache(collections.MutableMapping):
    
    def __init__(self, session, project_root):
        
        self.session = session
        
        self.project_root = os.path.abspath(project_root)
        if not os.path.exists(project_root):
            os.makedirs(project_root)
            
        self.conn = sqlite3.connect(os.path.join(project_root, '.sgfs-cache.sqlite'))
        self.conn.text_factory = str
        
        with self.conn:
            self.conn.execute('CREATE TABLE IF NOT EXISTS entity_paths (entity_type TEXT, entity_id INTEGER, path TEXT)')
            self.conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS entity_paths_entity ON entity_paths(entity_type, entity_id)')
    
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
            return os.path.abspath(os.path.join(self.project_root, row[0]))
    
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
                yield self.session.merge(dict(type=row[0], id=row[1]))
    
        