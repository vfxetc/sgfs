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
                
        # Non-dicts (including Entities) don't matter; just pass them through.
        if not isinstance(data, dict):
            return data
            
        # Pass through entities if they are owned by us.
        if isinstance(data, Entity):
            if data.session is not self:
                raise ValueError('entity not owned by this session')
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
        return self.merge(self.shotgun.find_one(type_, filters, fields, *args, **kwargs))
    
    def fetch_heirarchy(self, entities):
        """Populate the parents as far up as we can go."""
        
        to_resolve = []
        while entities or to_resolve:

            # Go as far up as we already have for the specified entities.
            for entity in entities:
                while entity.parent(fetch=False):
                    entity = entity.parent()
                if entity['type'] != 'Project':
                    to_resolve.append(entity)
            
            # Bail.
            if not to_resolve:
                break
            
            # Find the type that we have the most entities of.
            types = {}
            for x in to_resolve:
                types.setdefault(x['type'], []).append(x)
            entities = max(types.itervalues(), key=len)
            
            # Remove them from the list to resolve.
            to_resolve = [x for x in to_resolve if x['type'] != entities[0]['type']]
            
            # Fetch the parent names.
            type_ = entities[0]['type']
            ids = list(set([x['id'] for x in entities]))
            parent_name = _parent_fields[type_]
            self.find(type_, [['id', 'in'] + ids], [parent_name])
    

    
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
    
    def pprint(self, depth=0, visited=None):
        print '%s:%s at 0x%x;' % (self.get('type'), self.get('id'), id(self)),
        
        visited = visited or set()
        if id(self) in visited:
            print '...'
            return
        visited.add(id(self))
        
        if len(self) <= 2:
            print '{}'
            return
        
        print '{' 
        depth += 1
        for k, v in sorted(self.iteritems()):
            if k in ('id', 'type'):
                continue
            if isinstance(v, Entity):
                print '%s%s =' % ('\t' * depth, k),
                v.pprint(depth)
            else:
                print '%s%s = %r' % ('\t' * depth, k, v)
        depth -= 1
        print '\t' * depth + '}'
                
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
        raise RuntimeError("cannot copy %s" % self.__class__.__name__)
    
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
    
