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
    
    def context_from_entities(self, entities):
        """Construct a Context graph which includes all of the given entities."""
        
        # If we are given a project then use it for the cache, otherwise query
        # the 'project.Project.code' for all provided original entities.
        pass
    
    def _fetch_entity_parents(self, entities):
        
        cache = {}
        entities = copy.deepcopy(list(entities))
        to_resolve = entities[:]
        
        while to_resolve:
            entity = to_resolve.pop(0)
            
            cache_key = (entity['type'], entity['id'])
            if cache_key in cache:
                continue
            cache[cache_key] = entity
            
            # Figure out where to find parents.
            parent_attr = utils.parent_fields.get(entity['type'])
            
            # Doesn't have a parent.
            if not parent_attr:
                continue

            # It is already there.
            if parent_attr in entity:
                to_resolve.append(entity[parent_attr])
                continue
            
            # Get the parent.
            parent = self.shotgun.find(entity['type'], [
                ('id', 'is', entity['id']),
            ], (parent_attr, ))[0][parent_attr]
            parent_key = (parent['type'], parent['id'])
            if parent_key in cache:
                parent = cache[parent_key]
            else:
                to_resolve.append(parent)
            
            # Mark it down.
            entity[parent_attr] = parent
        
        return entities
        
        # Find all parents that we don't know about until everything is rooted
        # at a single Project. Look for them in the path cache, eventually.
        
        # Error if there are multiple projects.
        
        # Reverse the parent relationships to construct a Context graph
        
        pass
