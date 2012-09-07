import itertools


class Session(object):
    
    def __init__(self, shotgun=None):
        self.shotgun = shotgun
        self.cache = {}
    
    def __getattr__(self, name):
        return getattr(self.shotgun, name)
    
    def merge(self, *args, **kwargs):
        
        # Get our one argument.
        if len(args) > 1 or args and kwargs:
            raise ValueError('must provide one arg or kwargs, not both')
        data = args[0] if args else kwargs
                
        # Non-dicts don't matter; just pass them through.
        if not isinstance(data, dict):
            return data
        
        if isinstance(data, Entity):
            
            # We already own it; pass it through.
            if data.session is self:
                return data
            
            # Another session owns it; error.
            if data.session is not self:
                raise ValueError('entity is already in a session')
            
            # Something else is already in this session for this key; error.
            if data.cache_key in self.cache:
                raise ValueError('%r is already in the session' % data.cache_key)
            
            # This is new! Take ownership and cache it.
            # TODO; take ownership of all of its contents.
            data.session = self
            self.cache[data.cache_key] = data
            return data
        
        # If it already exists, then merge this into the old one.
        new = Entity(data.get('type'), data.get('id'), self)
        key = new.cache_key
        if key in self.cache:
            entity = self.cache[key]
            entity.update(data)
            return entity
        
        # Return the new one.
        self.cache[key] = new
        new.update(data)
        return new
    
    def create(self, type_, data):
        return self.merge(self.shotgun.create(type_, data))

    def update(self, type_, id, data):
        return self.merge(self.shotgun.update(type_, id, data))

    def batch(self, requests):
        return [self.merge(x) if isinstance(x, dict) else x for x in self.shotgun.batch(requests)]
    
    def find(self, type_, filters, fields=None, *args, **kwargs):
        return [self.merge(x) for x in self.shotgun.find(type_, filters, fields, *args, **kwargs)]
    
    def find_one(self, type_, filters, fields=None, *args, **kwargs):
        x = self.merge(self.shotgun.find_one(type_, filters, fields, *args, **kwargs))
        # # # print 'FIND_ONE', x
        return x
        

    
_parent_fields = {
    'Task': 'entity',
    'Shot': 'sg_sequence',
    'Sequence': 'project',
    'Asset': 'project',
    'Project': None,
}


class Entity(dict):
    
    def __repr__(self):
        return '<Entity %s:%s at 0x%x; %s>' % (self.get('type'), self.get('id'), id(self), dict.__repr__(self))
    
    @staticmethod
    def _cache_key(data):
        type_ = data.get('type')
        id_ = data.get('id')
        if type_ and id_:
            return (type_, id_)
        elif type_:
            return ('New-%s' % type_, id(data))
        else:
            return ('Unknown', id_)
    
    @property
    def cache_key(self):
        return self._cache_key(self)
        
    def __init__(self, type_, id_, session):
        dict.__init__(self, type=type_, id=id_)
        self.session = session
    
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, self.session.merge(value))
    
    def setdefault(self, key, value):
        dict.setdefault(self, key, self.session.merge(value))
    
    def update(self, *args, **kwargs):
        for x in itertools.chain(args, [kwargs]):
            self._update(self, x, 0)
    
    def _update(self, dst, src, depth):
        # print ">>> MERGE", depth, dst, '<-', src
        for k, v in src.iteritems():
            
            if isinstance(v, dict):
                v = self.session.merge(v)
                # If the destination is not an entity, or the type or ID does
                # not match (and so is a different entity) then replace it.
                if (not isinstance(dst.get(k), Entity) or
                    dst[k] is v or
                    dst[k]['type'] != v['type'] or
                    dst[k]['id']   != v['id']
                ):
                    dst[k] = v
                else:
                    self._update(dst[k], v, depth + 1)
            else:
                dst[k] = v
        # print "<<< MERGE", depth, dst
        
    
    def copy(self):
        raise RuntimeError("Cannot copy Entities")
    
    def fetch(self, fields, force=False):
        # print 'FETCH', self, fields
        if force or any(x not in self for x in fields):
            # The session will automatically update us since we are cached.
            self.session.find_one(
                self['type'],
                [('id', 'is', self['id'])],
                fields,
            )
    
    def parent(self, fetch=True):
        name = _parent_fields[self['type']]
        if fetch:
            self.fetch([name])
            self.setdefault(name, None)
        return self.get(name)
    
    def fetch_to_project(self):
        pass
        
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
    
