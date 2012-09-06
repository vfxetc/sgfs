import os
import copy

import shotgun_api3_registry

from .shotgun import Session


class SGFS(object):
    
    def __init__(self, root=None, project=None, shotgun=None):
        
        if root is None:
            root = os.environ.get('SGFS_ROOT')
        if root is None:
            raise ValueError('root or $SGFS_ROOT must not be None')
        self.root = root
        
        self.project = project
        self.shotgun = shotgun
        self.session = Session(self.shotgun)
        
    
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
