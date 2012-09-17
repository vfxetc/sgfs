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
    
    def __init__(self, root, session=None, shotgun=None):
        
        self.root = root
        
        # Set the session.
        if not shotgun and not session:
            raise ValueError('one of session or shotgun must not be provided')
        self.session = session or Session(shotgun)
        
        # Scan the root looking for Project tags in its top level.
        self.project_roots = {}
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            for tag in self.get_directory_entity_tags(path):
                if tag['entity']['type'] == 'Project':
                    self.project_roots[tag['entity']] = path
    
    def path_cache(self, project):
        project_root = self.project_roots.get(project)
        if project_root is None:
            return
        else:
            return PathCache(self.session, project_root)
    
    def path_for_entity(self, entity):
        """Get the path on disk for the given entity.
        
        This only works if the entity has been previously tagged, either by a
        manual process, of if the structure was automatically tagged or created
        by SGFS.
        
        """
        if entity['type'] == 'Project':
            return self.project_roots.get(entity)
        else:
            project = entity.project()
            path_cache = self.path_cache(project)
            if path_cache is not None:
                return path_cache.get(entity)
            
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
        with open(os.path.join(path, '.sgfs.yml'), 'a') as fh:
            fh.write(serialized)
        
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
    
    def entities_from_path(self, path):
        while path and path != '/':
            tags = self.get_directory_entity_tags(path)
            if tags:
                return self.session.merge([x['entity'] for x in tags])
            path = os.path.dirname(path)
        return []
    
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
        
        # TODO: If we are given a project then use it for the cache, otherwise
        # query the 'project.Project.code' for all provided original entities.
        # TODO: load these from the cache once we have a project
        entities = self.session.merge(entities)
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
    
    def _structure_from_entities(self, entities, schema_name):
        context = self.context_from_entities(entities)
        return Schema(schema_name).structure(context)
    
    def create_structure(self, entities, schema_name=None, verbose=False, dry_run=False):
        structure = self._structure_from_entities(entities, schema_name)
        return structure.create(self.root, verbose=verbose, dry_run=dry_run)
    
    def tag_existing_structure(self, entities, schema_name=None, verbose=False, dry_run=False):
        structure = self._structure_from_entities(entities, schema_name)
        structure.tag_existing(self.root, verbose=verbose)
    
    
