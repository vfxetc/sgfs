
class Session(object):
    
    def __init__(self, shotgun=None):
        self.shotgun = shotgun
        self.cache = {}
    
    def __getattr__(self, name):
        return getattr(self.shotgun, name)
    
    def as_entity(self, data):
        if isinstance(data, Entity):
            return data
        key = Entity._cache_key(data)
        if key in self.cache:
            entity = self.cache[key]
            entity.merge(data)
            return entity
        return Entity(data, self)
    
    def create(self, type_, data):
        return self.as_entity(self.shotgun.create(type_, data))

    def update(self, type_, id, data):
        return self.as_entity(self.shotgun.update(type_, id, data))

    def batch(self, requests):
        return [self.as_entity(x) if isinstance(x, dict) else x for x in self.shotgun.batch(requests)]
    
    def find(self, type_, filters, fields=None, *args, **kwargs):
        return [self.as_entity(x) for x in self.shotgun.find(type_, filters, fields, *args, **kwargs)]
    
    def find_one(self, type_, filters, fields=None, *args, **kwargs):
        return self.as_entity(self.shotgun.find_one(type_, filters, fields, *args, **kwargs))
        

    
_parent_fields = {
    'Task': 'entity',
    'Shot': 'sg_sequence',
    'Sequence': 'project',
    'Asset': 'project',
    'Project': None,
}


class Entity(dict):
    
    @staticmethod
    def _cache_key(data):
        try:
            return (data['type'], data['id'])
        except KeyError:
            return id(data)
    
    @property
    def cache_key(self):
        return self._cache_key(self)
        
    def __init__(self, data, session):
        super(Entity, self).__init__(data)
        
        self.session = session
        self.session.cache[self.cache_key] = self
        
        # Recursively resolve child entities.
        for k, v in self.items():
            if isinstance(v, dict) and 'type' in v:
                self[k] = self.__class__(v, session=session)
    
    def merge(self, other):
        self._merge_dict(self, other)
    
    def _merge_dict(self, dst, src):
        for k, v in src.iteritems():
            if isinstance(v, dict):
                self._merge_dict(dst.setdefault(k, {}), v)
            else:
                dst[k] = v
    
    def copy(self):
        raise RuntimeError("Cannot copy Entities")
    
    def fetch(self, fields, force=False):
        if force or any(x not in self for x in fields):
            # The session will automatically update us since we are cached.
            self.session.find_one(
                self['type'],
                [('id', 'is', self['id'])],
                fields,
            )
    
    def parent(self, fetch=True):
        name = _parent_fields[self['type']]
        if name in self:
            return self[name]
        if fetch:
            self[name] = self.session.find_one()
        return entity.get(parent_fields.get(entity['type']))
        
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
    
