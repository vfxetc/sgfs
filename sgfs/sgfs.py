from __future__ import with_statement

from pprint import pprint
import copy
import datetime
import os

import yaml

from sgsession import Session

from .context import Context
from .schema import Schema
from .cache import PathCache

TAG_NAME = '.sgfs.yml'


class SGFS(object):
    
    def __init__(self, root=None, session=None, shotgun=None):
        
        if root is None:
            root = os.environ.get('SGFS_ROOT')
        if root is None:
            raise ValueError('root or $SGFS_ROOT must not be None')
        self.root = root
        
        if not (shotgun or session):
            raise ValueError('one of session or shotgun must not be None')
        if shotgun and session:
            raise ValueError('session or shotgun, but not both')
        if shotgun:
            self.shotgun = shotgun
            self.session = Session(self.shotgun)
        else:
            self.session = session
            self.shotgun = session.shotgun
    
    @property
    def project_roots(self):
        try:
            return self._project_roots
        except AttributeError:
            pass
        
        self._project_roots = roots = {}
        
        # Scan the root looking for Project tags in all directories therein.
        for name in os.listdir(self.root):
            path = os.path.join(self.root, name)
            for tag in self.get_directory_tags(path):
                if tag['entity']['type'] == 'Project':
                    roots[tag['entity']] = path
        
        return roots
    
    def path_cache(self, project):
        project_root = self.project_roots.get(project)
        if project_root is None:
            return
        else:
            return PathCache(self.session, project_root)
    
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
        with open(os.path.join(path, TAG_NAME), 'a') as fh:
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
    
    def get_directory_tags(self, path):
        path = os.path.join(path, TAG_NAME)
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            tags = list(yaml.load_all(fh.read()))
            for tag in tags:
                tag['entity'] = self.session.merge(tag['entity'])
            return tags
    
    def context_from_path(self, path):
        entities = []
        while path and path != '/':
            for tag in self.get_directory_tags(path):
                entities.append(tag['entity'])
                if tag['entity']['type'] == 'Project':
                    return self.context_from_entities(entities)
            path = os.path.dirname(path)
        return
    
    def context_from_entities(self, entities):
        """Construct a Context graph which includes all of the given entities."""
        
        if isinstance(entities, dict):
            entities = [entities]
        
        # TODO: If we are given a project then use it for the cache, otherwise
        # query the 'project.Project.code' for all provided original entities.
        # TODO: load these from the cache once we have a project
        entities = [self.session.merge(x) for x in entities]
        self.session.fetch_heirarchy(entities)
        
        projects = filter(None, (x if x['type'] == 'Project' else x.project() for x in entities))
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
    
    def schema(self, name='v1', entity_type='Project'):
        schema_root = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'schemas',
            name,
        )
        if not os.path.exists(schema_root):
            raise ValueError('schema %r does not exist' % name)
        return Schema(schema_root, entity_type, entity_type + '.yml')
    
    def create_structure(self, entities, verbose=False, preview=False):
        if isinstance(entities, dict):
            entities = [entities]
        merged = [self.session.merge(x) for x in entities]
        context = self.context_from_entities(merged)
        schema = self.schema('v1')
        structure = schema.structure(context)
        if preview:
            return structure.preview(self.root, verbose=verbose)
        else:
            return structure.create(self.root, verbose=verbose)
    
    
