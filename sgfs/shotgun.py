
class Session(object):
    
    def __init__(self, shotgun):
        self.shotgun = shotgun
        self.cache = {}
    
    def __getattr__(self, name):
        return getattr(self.shotgun, name)
    
    def _entityfy(self, data):
        if isinstance(data, Entity):
            return data
        key = Entity._cache_key(data)
        if key in self.cache:
            entity = self.cache[key]
            entity.merge(data)
            return entity
        return Entity(data, _session=self)
    
    def create(self, type_, data):
        return self._entityfy(self.shotgun.create(type_, data))

    def update(self, type_, id, data):
        return self._entityfy(self.shotgun.update(type_, id, data))

    def batch(self, requests):
        return [self._entityfy(x) if isinstance(x, dict) else x for x in self.shotgun.batch(requests)]
    
    def find(self, type_, filters, fields=None, *args, **kwargs):
        return [self._entityfy(x) for x in self.shotgun.find(type_, filters, fields, *args, **kwargs)]


class Entity(dict):
    
    @staticmethod
    def _cache_key(data):
        return (data['type'], data['id'])
    
    @property
    def cache_key(self):
        return self._cache_key(self)
        
    def __init__(self, data={}, _session=None, **kwargs):
        
        self._session = _session
        
        self.update(data)
        self.update(kwargs)
        
        # Recursively resolve child entities.
        for k, v in self.items():
            if isinstance(v, dict) and 'type' in v:
                self[k] = self.__class__(v, _session=_session)
    
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
    
