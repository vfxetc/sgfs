class ChildList(list):
    
    def pop(self, key, *args):
        
        if isinstance(key, int):
            return super(ChildList, self).pop(key, *args)
        
        for i, child in enumerate(self):
            if child.key == key:
                break
        else:
            if args:
                return args[0]
            else:
                raise KeyError(key)
        return self.pop(i)
    
    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default
        
    def __getitem__(self, key):
        if not isinstance(key, int):
            for child in self:
                if child.key == key:
                    return child
            raise KeyError(key)
        return super(ChildList, self).__getitem__(key)

