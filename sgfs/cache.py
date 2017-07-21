from subprocess import call
import collections
import errno
import logging
import os
import sqlite3

from sgsession import Entity


log = logging.getLogger(__name__)


class PathCache(collections.MutableMapping):
    
    def __init__(self, sgfs, project_root, name=None):
        
        self.sgfs = sgfs
        self.dir_map = sgfs.dir_map
        self.project_root = os.path.abspath(project_root)
        
        # In the beginning, the cache was a single SQLite file called ``.sgfs-cache.sqlite``,
        # and then it was moved to ``.sgfs/cache.sqlite``. Finally, we started
        # supporting multiple named caches with ``.sgfs/cache/{name}.sqlite``.
        # We will read from them all, and write to one.

        cache_dir = os.path.join(project_root, '.sgfs', 'caches')

        self.write_name = name or os.environ.get('SGFS_CACHE', '500-primary')
        self.write_path = os.path.join(cache_dir, self.write_name + '.sqlite')
        read_paths = [self.write_path]

        # Check for old caches.
        for name in ('.sgfs-cache.sqlite', '.sgfs/cache.sqlite'):
            path = os.path.join(project_root, name)
            if os.path.exists(path):
                read_paths.append(path)

        # Find all caches.
        try:
            names = os.listdir(cache_dir)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            names = []
        for name in names:
            if name.startswith('.'):
                continue
            if not name.endswith('.sqlite'):
                continue
            read_paths.append(os.path.join(cache_dir, name))

        # We sort them so that they are always in a predictable order regardless
        # of which is the writer and the behaviour of the filesystem.
        self.read_paths = sorted(set(read_paths))

        # If it doesn't exist then touch it with read/write permissions for all.
        if not os.path.exists(self.write_path):
            db_dir = os.path.dirname(self.write_path)
            umask = os.umask(0)
            try:
                try:
                    os.makedirs(db_dir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                os.umask(0111)
                call(['touch', self.write_path]) # So hacky.
            finally:
                os.umask(umask)
        
        with self.write_con() as con:
            con.execute('CREATE TABLE IF NOT EXISTS entity_paths (entity_type TEXT, entity_id INTEGER, path TEXT)')
            con.execute('CREATE UNIQUE INDEX IF NOT EXISTS entity_paths_entity ON entity_paths(entity_type, entity_id)')
    
    def _connect(self, path):
        con = sqlite3.connect(path)
        con.text_factory = str
        return con

    def write_con(self):
        return self._connect(self.write_path)

    def read_cons(self):
        for path in self.read_paths:
            yield self._connect(path)

    def __repr__(self):
        return '<%s for %r at 0x%x>' % (self.__class__.__name__, self.project_root, id(self))
    
    def __setitem__(self, entity, path):
        
        if not isinstance(entity, Entity):
            raise TypeError('path cache keys must be entities; got %r %r' % (type(entity), entity))
        if not isinstance(path, basestring):
            raise TypeError('path cache values must be basestring; got %r %r' % (type(path), path))
        

        path = os.path.abspath(path)
        project_root = self.project_root

        # os.path.relpath, but only if the path is within.
        if path.startswith(project_root):
            if len(path) == len(project_root):
                path = '.'
            elif path[len(project_root)] == os.path.sep:
                path = path[len(project_root) + 1:]

        with self.write_con() as con:
            con.execute('INSERT OR REPLACE into entity_paths values (?, ?, ?)', (entity['type'], entity['id'], path))
    
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

        path = default
        for con in self.read_cons():
            cur = con.execute('''
                SELECT
                    path
                FROM entity_paths
                WHERE
                    entity_type = ? AND
                    entity_id = ?
                LIMIT 1
            ''', (entity['type'], entity['id']))
            row = next(cur, None)
            if row is None:
                continue

            # DirMap the external ones, and make the internal ones absolute.
            path = row[0]
            if os.path.isabs(path):
                path = self.dir_map(path)
            else:
                # Need to normpath because very old caches might be strange.
                path = os.path.normpath(os.path.join(self.project_root, path))

            # Make sure that the entity is actually tagged in the given directory.
            # This guards against moving tagged directories. This does NOT
            # effectively guard against copied directories.
            if check_tags and not any(
                tag['entity'] is entity for tag in self.sgfs.get_directory_entity_tags(path)
            ):
                log.warning('%s %d is not tagged at %s' % (
                    entity['type'], entity['id'], path,
                ))
                continue

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
        len_ = 0
        for con in self.read_cons():
            len_ += next(con.execute('''SELECT COUNT(1) FROM entity_paths'''))[0]
        return len_
    
    def __iter__(self):
        for con in self.read_cons():
            for row in con.execute('''SELECT entity_type, entity_id FROM entity_paths'''):
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

        for con in self.read_cons():

            if entity_type is not None:
                cur = con.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE entity_type = ? AND path LIKE ?', (entity_type, root_path + '%'))
            else:
                cur = con.execute('SELECT entity_type, entity_id, path FROM entity_paths WHERE path LIKE ?', (root_path + '%', ))
            
            for row in cur:
                entity = self.sgfs.session.merge(dict(type=row[0], id=row[1]))
                path = os.path.normpath(os.path.join(self.project_root, row[2]))
                if must_exist and not os.path.exists(path):
                    continue
                yield path, entity

