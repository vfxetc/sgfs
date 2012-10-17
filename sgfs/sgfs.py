from pprint import pprint
import copy
import datetime
import os

import yaml

from sgsession import Session

from .cache import PathCache
from .context import Context
from .schema import Schema


class SGFS(object):
    
    """The mapping from Shotgun to the file system.
    
    :param str root: The location of projects on disk. Defaults to ``$SGFS_ROOT``.
    :param session: The :class:`~sgsession.session.Session` to use. Defaults to
        a clean wrapper around the given ``shotgun``.
    :param shotgun: The ``Shotgun`` API to use. Defaults to an automatically
        constructed instance via ``shotgun_api3_registry``.
    
    """
    
    def __init__(self, root=None, session=None, shotgun=None):
        
        # Take the given root, or look it up in the environment.
        if root is None:
            root = os.environ.get('SGFS_ROOT')
            if root is None:
                raise ValueError('one of root or $SGFS_ROOT must not be None')
        self.root = os.path.abspath(root)
        
        # Set the session, building it from a generic Shotgun if nothing was
        # given. This requires a `shotgun_api3_registry.connect()` function.
        if not shotgun and not session:
            import shotgun_api3_registry
            shotgun = shotgun_api3_registry.connect(auto_name_stack_depth=1)
        self.session = session or Session(shotgun)
        
        # Scan the root looking for Project tags in its top level.
        self.project_roots = {}
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            for tag in self.get_directory_entity_tags(path):
                if tag['entity']['type'] == 'Project':
                    self.project_roots[tag['entity']] = path
    
    def path_cache(self, project):
        """Get a :class:`~sgfs.cache.PathCache` for a given path or entity..
        
        :param project: Either a ``str`` path within a project, or an
            :class:`~sgsession.entity.Entity`.
        :return: A :class:`~sgfs.cache.PathCache` or ``None``.
        
        """
        if isinstance(project, basestring):
            path = os.path.abspath(project)
            for project_root in self.project_roots.itervalues():
                if path.startswith(project_root):
                    return PathCache(self, project_root)
            return
        
        project = project.project()
        project_root = self.project_roots.get(project)
        if project_root is not None:
            return PathCache(self, project_root)
    
    def path_for_entity(self, entity):
        """Get the path on disk for the given entity.
        
        :param entity: An :class:`~sgsession.entity.Entity`
        :return: ``str`` if the entity has a tagged directory, or ``None``.
        
        This only works if the entity has been previously tagged, either by a
        manual process, of if the structure was automatically tagged or created
        by SGFS.
        
        This will also only return a still valid path, since the path cache
        will verify that the returned directory is still tagged with the given
        entity.
        
        E.g.::
        
            >>> # We want a path for this task...
            >>> sgfs.path_for_entity({"type": "Task", "id": 43898})
            '<snip>/SEQ/GC/GC_001_001/Light'
            
            >>> # This one doesn't exist...
            >>> sgfs.path_for_entity({"type": "Task", "id": 123456})
            None
            
        """
        
        entity = self.session.merge(entity)
        
        # Projects are special cased; we should always know the paths to all
        # projects.
        if entity['type'] == 'Project':
            return self.project_roots.get(entity)
        
        # If we already know the project for this entity, then look it up in the
        # project_roots.
        project = entity.project(fetch=False)
        if project is not None:
            path_cache = self.path_cache(project)
            return path_cache.get(entity) if path_cache is not None else None
        
        # It should be cheaper to hit the disk to poll all caches than to query
        # the Shotgun server for the project.
        for project in self.project_roots:
            path_cache = self.path_cache(project)
            path = path_cache.get(entity) if path_cache is not None else None
            if path is not None:
                return path
    
    def tag_directory_with_entity(self, path, entity, cache=True):
        """Tag a directory with the given entity, and add it to the cache.
        
        This allows us to associate entities with directories, and the reverse.
        
        :param str path: The directory to tag.
        :param entity: The :class:`~sgsession.entity.Entity` to tag it with.
        :param bool cache: Add this to the path cache?
        
        """
        tag = {
            'created_at': datetime.datetime.now(),
            'entity': entity.as_dict(),
        }
        serialized = yaml.dump(tag,
            explicit_start=True,
            indent=4,
            default_flow_style=False
        )
        
        # Write the tag, and set the permissions on it.
        tag_path = os.path.join(path, '.sgfs.yml')
        umask = os.umask(0111) # Race condition when threaded?
        with open(tag_path, 'a') as fh:
            fh.write(serialized)
        os.umask(umask)
            
        # Add it to the local project roots.
        if entity['type'] == 'Project':
            self.project_roots[entity] = path
        
        # Add to path cache.
        if cache:
            path_cache = self.path_cache(entity.project())
            if path_cache is None:
                raise ValueError('could not get path cache for %r from %r' % (entity.project(), entity))
            path_cache[entity] = path
    
    def get_directory_entity_tags(self, path):
        """Get the tags for the given directory.
        
        :param str path: The directory to get tags for.
        :return: ``list`` of ``dict``.
        
        """
        path = os.path.join(path, '.sgfs.yml')
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            tags = list(yaml.load_all(fh.read()))
            for tag in tags:
                tag['entity'] = self.session.merge(tag['entity'])
            return tags
    
    def entities_from_path(self, path):
        """Get the most specific entities that have been tagged in a parent
        directory of the given path.
        
        :param str path: The path to find entities for.
        :return: ``tuple`` of :class:`~sgsession.entity.Entity`.
        
        E.g.::
            
            >>> # Get a few lighting tasks.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_001/Light')
            (<Entity Task:43897 at 0x1011b9c0>, <Entity Task:43990 at 0x10112da7>)
            
            >>> # Get the shot.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_001')
            (<Entity Shot:5801 at 0x1011c03d0>,)
        
        """
        path = os.path.abspath(path)
        while path and path != '/':
            tags = self.get_directory_entity_tags(path)
            if tags:
                return self.session.merge([x['entity'] for x in tags])
            path = os.path.dirname(path)
        return ()
    
    def entities_in_directory(self, path, entity_type=None, load_tags=False):
        """Iterate across every :class:`~sgsession.entity.Entity` within the
        given directory.
        
        This uses the path cache to avoid actually walking the directory.
        
        :param str path: The path to walk for entities.
        :param str entity_type: Restrict to this type; None returns all.
        :param bool load_tags: Load data cached in tags? None implies automatic.
        :return: Iterator of ``(path, entity)`` tuples.
        
        E.g.::
        
            >>> # Get everything under this shot, including the Shot and Tasks.
            >>> for x in sgfs.entities_in_directory('SEQ/GC/GC_001_001'):
            ...     print x
            ('<snip>/SEQ/GC/GC_001_001', <Entity Shot:5801 at 0x1011bb720>)
            ('<snip>/SEQ/GC/GC_001_001/Anim', <Entity Task:43897 at 0x1011bc0c0>)
            ('<snip>/SEQ/GC/GC_001_001/Light', <Entity Task:43898 at 0x1011bee80>)
            
        """
        path = os.path.abspath(path)
        cache = self.path_cache(path)
        for path, entity in cache.walk_directory(path, entity_type):
            if load_tags or (load_tags is None and len(entity) == 2):
                self.get_directory_entity_tags(path)
            yield path, entity
    
    def rebuild_cache(self, path):
        """Walk a directory looking for tags, and rebuild the cache for them.
        
        This is useful when a tagged directory has been moved, breaking the
        reverse path cache. Rebuilding the cache of that directory using this
        method will reconnect the tags to the path cache.
        
        :param str path: The path to walk and rebuild the cache for.
        :raises ValueError: when ``path`` is not within a project.
        
        """
        cache = self.path_cache(path)
        if cache is None:
            raise ValueError('Could not get path cache from %r' % path)
        for dir_path, dir_names, file_names in os.walk(path):
            for tag in self.get_directory_entity_tags(dir_path):
                cache[tag['entity']] = dir_path
    
    def context_from_entities(self, entities):
        """Construct a :class:`~sgfs.context.Context` graph which includes all
        of the given entities.
        
        A ``Project`` must be reachable from every provided entity, and they
        must all reach the same ``Project``.
        
        :param list entities: A ``list`` of :class:`~sgsession.entity.Entity`
            (or bare ``dict``) to get the context of.
        :returns: A :class:`~sgfs.context.Context` rooted at the ``Project``,
            including the given ``entities`` as leafs.
        :raises ValueError: when the project conditions are not satisfied.
        
        E.g.::
            
            >>> sgfs.context_from_entities([{"type": "Task", "id": 43990}]).pprint()
            Project:66 -> Sequence:101 -> Shot:5801 -> Task:43990
        
        """
        
        # Accept a single instance as well.
        if isinstance(entities, dict):
            entities = [entities]
        
        # Assert that they are entities.
        entities = self.session.merge(entities)
        
        # If we don't already have the parent of the entity then populate as
        # much as we can from the cache.
        for entity in entities:
            if entity.parent(fetch=False) and entity.project(fetch=False):
                continue
            path = self.path_for_entity(entity)
            if path:
                self.get_directory_entity_tags(path)
        
        self.session.fetch_heirarchy(entities)
        
        # Assert project conditions.
        projects = filter(None, (x.project(fetch=False) for x in entities))
        if len(projects) != len(entities):
            raise ValueError('given entities do not all have projects')
        if len(set(projects)) != 1:
            raise ValueError('given entities have multiple projects')
        
        # Reverse the parent relationships to construct a Context graph
        entity_to_context = {}
        to_resolve = list(entities)
        while to_resolve:
            
            # Grab an entity to resolve, build a context for it if it doesn't
            # already exist, and finish with it if it is the project.
            entity = to_resolve.pop(0)
            try:
                context = entity_to_context[entity]
            except KeyError:
                context = Context(self, entity)
                entity_to_context[entity] = context
            
            if entity['type'] == 'Project':
                continue
            
            # Grab the entity's parent, link it up of it already has a context
            # otherwise reschedule them both for resolution.
            parent = entity.parent()
            try:
                parent_context = entity_to_context[parent]
            except KeyError:
                # It would be nice to use a different data structure. Oh well.
                if parent not in to_resolve:
                    to_resolve.append(parent)
                if entity not in to_resolve:
                    to_resolve.append(entity)
            else:
                parent_context.children.append(context)
                context.parent = parent_context
        
        # The project is the root.
        return entity_to_context[projects[0]]
    
    def context_from_path(self, path):
        """Get a :class:`~sgfs.context.Context` with every tagged
        :class:`~sgsession.entity.Entity` in the given path.
        
        :param str path: The path to return a context for.
        
        This walks upwards on the path specified until it finds a directory
        that has been tagged as a ``Project``, and then returns a context
        rooted at that project and containing every entity discovered up to that
        point.
        
        The returned graph may also be non-linear as a directory may be tagged
        more than once. More often than not this will be multiple tasks attached
        to the same entity, and so the fork will exist only in the last step.
        
        E.g.::
        
            >>> ctx = sgfs.context_from_path("SEQ/GC/GC_001_001/Anim")
            >>> ctx
            <Context Project:66 at 0x10183b510>
            >>> ctx.pprint()
            Project:66 -> Sequence:101 -> Shot:5801 {
            	Task:43897
            	Task:43990
            }
        
        An unambiguous (e.g. linear) context may look like:
        
        .. graphviz:: /_graphs/sgfs/context_from_path.0.dot
        
        If there is more than one task in the same path, the context
        may be ambiguous (e.g. non-linear), and may look like:
        
        .. graphviz:: /_graphs/sgfs/context_from_path.1.dot
        
        """
        entities = []
        path = os.path.abspath(path)
        while path and path != '/':
            for tag in self.get_directory_entity_tags(path):
                entities.append(tag['entity'])
                if tag['entity']['type'] == 'Project':
                    return self.context_from_entities(entities)
            path = os.path.dirname(path)
        return
            
    def _structure_from_entities(self, entities, schema_name):
        context = self.context_from_entities(entities)
        return Schema(schema_name).structure(context)
    
    def create_structure(self, entities, schema_name=None, **kwargs):
        """Create the structure on disk for the given entities.
        
        :param list entities: The set of :class:`~sgsession.entity.Entity` to
            create structure for.
        :param str schema_name: Which schema to use. Defaults to ``'v1'``
        :param bool dry_run: Don't actually create structure. Defaults to ``False``.
        :param bool verbose: Print out what is going on. Defaults to ``False``.
        :param bool allow_project: Allow creation of projects? Defaults to ``False``.
        :return: A ``list`` of steps taken.
        
        """
        structure = self._structure_from_entities(entities, schema_name)
        return structure.create(self.root, **kwargs)
    
    def tag_existing_structure(self, entities, schema_name=None, **kwargs):
        """Tag existing structures without creating new ones.
        
        :param list entities: The set of :class:`~sgsession.entity.Entity` to
            create structure for.
        :param str schema_name: Which schema to use. Defaults to ``'v1'``
        :param bool dry_run: Don't actually create structure. Defaults to ``False``.
        :param bool verbose: Print out what is going on. Defaults to ``False``.
        :return: ``dict`` mapping entities to paths.
        
        """
        structure = self._structure_from_entities(entities, schema_name)
        return dict(structure.tag_existing(self.root, **kwargs))
    
    
