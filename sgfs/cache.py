from subprocess import call
import collections
import errno
import logging
import os
import sqlite3

from sgsession import Entity


log = logging.getLogger(__name__)


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
        
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(abs_path, self.project_root)
        
        if rel_path.startswith(os.path.pardir + os.path.sep):
            path = abs_path
        else:
            path = rel_path


        with self.conn:
            self.conn.execute('INSERT OR REPLACE into entity_paths values (?, ?, ?)', (entity['type'], entity['id'], path))
    
    def get(self, entity, default=None, check_tags=True):
        """Get a path for an entity.

        :param Entity entity: The entity to look up in the path cache.
        :param default: What to return if the entity is not in the cache;
            defaults to ``None``.
        :param bool check_tags: Should we check for the entity in the directory
            tags at the cached path before returning it?
        :returns: The cached path.

        """

        if not isinstance(entity, Entity):
            raise TypeError('path cache keys are entities; got %r %r' % (type(entity), entity))

        with self.conn:
            c = self.conn.cursor()
            c.execute('SELECT path FROM entity_paths WHERE entity_type = ? AND entity_id = ?', (entity['type'], entity['id']))
            row = c.fetchone()
            if row is None:
                return default
            path = os.path.abspath(os.path.join(self.project_root, row[0]))

        # Make sure that the entity is actually tagged in the given directory.
        # This guards against moving tagged directories. This does NOT
        # effectively guard against copied directories.
        if check_tags:
            if not any(tag['entity'] is entity for tag in self.sgfs.get_directory_entity_tags(path)):
                log.warning('%s %d is not tagged at %s' % (
                    entity['type'], entity['id'], path,
                ))
                return default

        return path

    def __getitem__(self, entity):
        path = self.get(entity)
        if path is None:
            raise KeyError(entity)
        else:
            return path
    
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

        abs_path = os.path.abspath(path)
        root_path = os.path.relpath(abs_path, self.project_root)
        
        # Special case the Projects.
        if root_path == '.':
            root_path = ''
            
        # We're looking outside of the primary root.
        elif root_path.startswith(os.path.pardir + os.path.sep):
            root_path = abs_path

        with self.conn:

            c = self.conn.cursor()
            if entity_type is not None:
                c.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE entity_type = ? AND path LIKE ?', (entity_type, root_path + '%'))
            else:
                c.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE path LIKE ?', (root_path + '%', ))
            
            for row in c:
                entity = self.sgfs.session.merge(dict(type=row[0], id=row[1]))
                path = os.path.join(self.project_root, row[2])
                if must_exist and not os.path.exists(path):
                    continue
                yield path, entity

