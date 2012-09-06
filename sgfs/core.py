import os
import copy

import shotgun_api3_registry

from . import utils


class SGFS(object):
    
    def __init__(self, root=None, project=None, shotgun=None):
        
        if root is None:
            root = os.environ.get('SGFS_ROOT')
        if root is None:
            raise ValueError('root or $SGFS_ROOT must not be None')
        self.root = root
        
        self.project = project
        
        self.shotgun = shotgun or shotgun_api3_registry.connect(__test__)
    
    def _fetch_entity_parents(self, entities):
        """Assert a full parental chain all the way up to the root Projects.
        
        TODO: Fetch this from tags on disk.
        
        Note: All equivalent entities will be the same dictionary.
        
        """
        
        cache = {}
        entities = copy.deepcopy(list(entities))
        to_resolve = entities[:]
        
        while to_resolve:
            entity = to_resolve.pop(0)
            
            cache_key = (entity['type'], entity['id'])
            cache[cache_key] = entity
            
            # Figure out where to find parents.
            parent_attr = utils.parent_fields.get(entity['type'])
            
            # Doesn't have a parent.
            if not parent_attr:
                continue

            # It is already there.
            if parent_attr in entity:
                parent = entity[parent_attr]
            
            # Get the parent.
            else:
                parent = self.shotgun.find(entity['type'], [
                    ('id', 'is', entity['id']),
                ], (parent_attr, ))[0][parent_attr]
            
            parent_key = (parent['type'], parent['id'])
            parent = cache.setdefault(parent_key, parent)
            
            # Mark it down, and prepare for next loop.
            entity[parent_attr] = parent
            to_resolve.append(parent)
        
        return entities
    
    def context_from_entities(self, entities):
        """Construct a Context graph which includes all of the given entities."""
            
        # Resolve all parents up to the Project.
        entities = self._fetch_entity_parents(entities)
        
        # Error if there are multiple projects.
        projects = set()
        for entity in entities:
            while parent(entity):
                entity = parent(entity)
            projects.add(entity['id'])
        if len(projects) != 1:
            raise ValueError('There is no common Project parent')
        
        # If we are given a project then use it for the cache, otherwise query
        # the 'project.Project.code' for all provided original entities.        
        
        # Reverse the parent relationships to construct a Context graph
        
        pass
