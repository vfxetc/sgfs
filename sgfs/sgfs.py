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
    
    def __init__(self, root=None, session=None, shotgun=None):
        
        # Take the given root, or look it up in the environment.
        if root is None:
            root = os.environ.get('SGFS_ROOT')
            if root is None:
                raise ValueError('one of root or $SGFS_ROOT must not be None')
        self.root = root
        
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
        
        if isinstance(project, basestring):
            for project_root in self.project_roots.itervalues():
                if project.startswith(project_root):
                    return PathCache(self, project_root)
            return
        
        project_root = self.project_roots.get(project)
        if project_root is not None:
            return PathCache(self, project_root)
    
    def path_for_entity(self, entity):
        """Get the path on disk for the given entity.
        
        This only works if the entity has been previously tagged, either by a
        manual process, of if the structure was automatically tagged or created
        by SGFS.
        
        """
        
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
        path = os.path.join(path, '.sgfs.yml')
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            tags = list(yaml.load_all(fh.read()))
            for tag in tags:
                tag['entity'] = self.session.merge(tag['entity'])
            return tags
    
    def entities_from_path(self, path):
        while path and path != '/':
            tags = self.get_directory_entity_tags(path)
            if tags:
                return self.session.merge([x['entity'] for x in tags])
            path = os.path.dirname(path)
        return []
    
    def entities_in_directory(self, path, entity_type=None, load_tags=False):
        """Iterate across entities within the given directory.
        
        This uses the path cache to avoid actually walking the directory.
        
        :param str path: The path to walk for entities.
        :param str entity_type: Restrict to this type; None returns all.
        :param bool load_tags: Load data cached in tags? None implies automatic.
        :return: Iterator of ``(path, entity)`` pairs.
        
        """
        cache = self.path_cache(path)
        for path, entity in cache.walk_directory(path, entity_type):
            if load_tags or (load_tags is None and len(entity) == 2):
                self.get_directory_entity_tags(path)
            yield path, entity
    
    def rebuild_cache(self, path):
        context = self.context_from_path(path)
        if not context:
            raise ValueError('could not find any existing entities in %r' % path)
        cache = self.path_cache(context.entity)
        for dir_path, dir_names, file_names in os.walk(path):
            for tag in self.get_directory_entity_tags(dir_path):
                cache[tag['entity']] = dir_path
    
    def context_from_entities(self, entities):
        """Construct a Context graph which includes all of the given entities."""

        if isinstance(entities, dict):
            entities = [entities]
        
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
        
        # The parent is the root.
        return entity_to_context[projects[0]]
    
    def context_from_path(self, path):
        """Get a :class:`Context` with all tagged :class:`Entity`s in the given path.
        
        :param str path: The path to return a context for.
        
        This walks upwards on the path specified until it finds a directory that
        has been tagged as a Project, and then returns it. While :class:`Context` graphs
        may be rooted at any entity type, the graph returned here will always
        be rooted at a Project.
        
        The returned graph may also be non-linear as a directory may be tagged
        more than once. More often than not this will be multiple tasks attached
        to the same entity, and so the fork will exist only in the last step.
        
        """
        entities = []
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
        structure = self._structure_from_entities(entities, schema_name)
        return structure.create(self.root, **kwargs)
    
    def tag_existing_structure(self, entities, schema_name=None, **kwargs):
        structure = self._structure_from_entities(entities, schema_name)
        return dict(structure.tag_existing(self.root, **kwargs))
    
    
