import collections
import functools
import itertools


def eval_expr_or_func(src, globals_, locals_=None):
    lines = src.strip().splitlines()
    if len(lines) > 1:
        # Surely I can create a function object directly with a compiled code
        # object, but I couldn't quit figure it out in the time that I allowed.
        # Ergo, we are evalling strings. Sorry.
        src = 'def _():\n' + '\n'.join('\t' + line for line in lines)
        locals_ = locals_ if locals_ is not None else {}
        code = compile(src, '<str>', 'exec')
        eval(code, globals_, locals_)
        try:
            return locals_['_']()
        except Exception, e:
            raise ValueError('Error while running %r -> %r' % (src, e))
    else:
        try:
            return eval(lines[0], globals_)
        except Exception, e:
            raise ValueError('Error while running %r -> %r' % (lines[0], e))


class cached_property(object):
    
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
    
    def __get__(self, instance, owner_type=None):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.__name__]
        except KeyError:
            value = self.func(instance)
            instance.__dict__[self.__name__] = value
            return value


class chain_map(collections.Mapping):
    
    def __init__(self, *maps):
        self._maps = maps
    
    def __getitem__(self, key):
        for map_ in self._maps:
            try:
                return map_[key]
            except KeyError:
                pass
        raise KeyError(key)
    
    def __len__(self):
        return len(set(itertools.chain(*self._maps)))
    
    def __iter__(self):
        visited = set()
        for map_ in self._maps:
            for k in map_:
                if k in visited:
                    continue
                visited.add(k)
                yield k


