import ast
import os
import re


class Template(object):
    
    """A template for formatting or matching/parsing file paths.
    
    Formatting is done via the builtin :meth:`python:str.format`. Matching is
    done via regular expressions constructed to mimick the given format.
    Matching does not take all parts of the format specification into account
    (currently on the type), and so it may be more lenient that it should be.
    
    While they may be used independantly, a :class:`BoundTemplate` is normally
    sourced via :meth:`.SGFS.find_template`, and so they will be relative to
    the real disk location of the coresponding
    :class:`~sgfs.structure.Structure` node.
    
    :param str format: A format string.
    :param str path: The path from which the format string is relative to.
    
    """
    
    _format_type_to_re = {
        'b': (r'[-+]?(?:0b)?[01]+', lambda x: int(x, 2)),
        'c': (r'.+', str),
        'd': (r'[-+]?\d+', int),
        'e': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'E': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'f': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'F': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'g': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'G': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'n': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', None),
        'o': (r'[-+]?(?:0o)?[0-7]+', lambda x: int(x, 8)),
        's': (r'.+', str),
        'x': (r'[-+]?(?:0[xX])?[\dA-Fa-f]+', lambda x: int(x, 16)),
        'X': (r'[-+]?(?:0[xX])?[\dA-Fa-f]+', lambda x: int(x, 16)),
        '%': (r'%', str),
        None: (r'.+', None),
    }
    
    _format_type_re = re.compile(r'''
        (?:
            ([{}])? # Fill.
            ([<>=\^]) # Align.
        )?
        ([+ -])? # Sign.
        (\#)? # Number prefix flag.
        (0)? # Zero padding flag.
        (\d+)? # Width.
        (,)? # Comma separation.
        (\.\d+)? # Precision.
        ([bcdeEfFgGnosxX%])? # Type.
        $
    ''', re.VERBOSE)
    
    _reverse_cache = {}
    
    def __init__(self, format_string):
        self.format_string = format_string
        # Cache the parsing stage.
        try:
            self.fields, self._field_parsers, self.reverse_pattern, self._reverse_re = self._reverse_cache[format_string]
        except KeyError:
            self._compile_reverse()
            self._reverse_cache[format_string] = self.fields, self._field_parsers, self.reverse_pattern, self._reverse_re
    
    def __repr__(self):
        return '<Template %r>' % (self.format_string)
    
    def _compile_reverse(self):
        
        self.fields = []
        self._field_parsers = []
        
        self.reverse_pattern = re.sub(r'{([^}]*)}', self._compile_reverse_sub, self.format_string)
        self._reverse_re = re.compile(self.reverse_pattern +'$')
        
        self.fields = tuple(self.fields)
        self._field_parsers = tuple(self._field_parsers)
        
    
    def _compile_reverse_sub(self, m):
        """Convert a field replacement to a regex which matches its output."""
        
        field_replacement = m.group(1)
        
        # Get the field name, and make sure it actually has a name.
        m = re.match(r'([\w\[\]\.]*)', field_replacement)
        field_name = m.group(1)
        if not field_name:
            raise ValueError('Template requires keyword fields')
        self.fields.append(field_name)
        
        # Parse the format_spec, but we are actually going to ignore most of it.
        m = re.search(r':(.+)', field_replacement)
        format_spec = m.group(1) if m else ''
        m = self._format_type_re.match(format_spec)
        if not m:
            raise ValueError('could not parse format spec %r' % format_spec)
        fill, align, sign, number_prefix, zero_pad, width, comma, precision, type_ = m.groups()
        
        # Get the pattern and parser, and finally return a RE.
        pattern, parser = self._format_type_to_re[type_]
        self._field_parsers.append(parser)
        return '(%s)' % (pattern)
    
    # `self_` so that `self` can be passed via kwargs.
    def format(self_, **kwargs):
        """Format the template with the given kwargs.
        
        :param dict **kwargs: Values to substitute into the pattern.
        :raises KeyError: When there is a missing value.
        
        ::
        
            >>> tpl = Template('{basename}_v{version:04d}{ext}')
            >>> tpl.format(basename='Awesome_Shot', version=123, ext='.ma')
            'Awesome_Shot_v0123.ma'
            
        """
        return self_.format_string.format(**kwargs)
    
    def match(self, input):
        """Match a name or path, returning a ``dict`` of fields if the input matched.
        
        :param str input: The name or path to attempt to parse.
        :returns: ``dict`` or ``None``.
        
        ::
        
            >>> tpl = Template('{basename}_v{version:04d}{ext}')
            >>> tpl.match('Awesome_Shot_v0123.ma')
            {'basename': 'Awesome_Shot', 'version': 123, 'ext': '.ma'}
        
        """
        m = self._reverse_re.match(input)
        if not m:
            return
        
        res = {}
        
        for field, parser, value in zip(self.fields, self._field_parsers, m.groups()):
            
            if parser is None:
                # Default parser tries to interpret as an int and float, and
                # finally gives up and turns it into a string.
                try:
                    literal = ast.literal_eval(value)
                except Exception:
                    pass
                else:
                    if isinstance(literal, (int, float)):
                        value = literal
            else:
                value = parser(value)
            
            # Assemble a dictionary of the same approximate shape as the imput
            # data. Unfortunately attributes will be converted into items, but
            # oh well.
            parts = re.split(r'[\s\[\]\.]+', field)
            parts = [x for x in parts if x]
            to_store = res
            while len(parts) > 1:
                to_store = to_store.setdefault(parts.pop(0), {})
            to_store[parts[0]] = value
        
        return res


class BoundTemplate(object):
    """A :class:`Template` relative to a path in the file system, with default
    values for entities in the context of that path.
    
    This behaves like a normal template, except it will :meth:`format` and
    :meth:`match` relative to a given path. It will also have a namespace
    including the entities in the context in which the sutrcture was created.
    For example, a template located in a ``Task`` schema config will have
    access to ``Task`` (also via ``self``) and ``Shot`` or ``Asset``, and all
    other entities up the chain to the ``Project``.
    
    :param str format: A format string, or a :class:`Template` instance.
    :param str path: The path from which the format string is relative to.
    :param dict namespace: The base values for the formatting operation.
    
    """
    
    
    def __init__(self, template, path, namespace=None):
        if isinstance(template, basestring):
            template = Template(template)
        
        #: The underlying :class:`Template`.
        self.template = template
        
        self.path = path
        self.namespace = namespace
    
    def __repr__(self):
        return '<BoundTemplate %r>' % os.path.join(self.path, self.template.format_string)
    
    # `self_` so that `self` can be passed via kwargs.
    def format(self_, **kwargs):
        """Format the template as a path with the given kwargs.
        
        The underlying template will be joined to the ``path`` given to the
        :class:`BoundTemplate` constructor.
        
        Also uses values from the ``namespace`` given to the constructor, but
        priority is given to values in ``**kwargs``.
        
        ::
            >>> tpl = BoundTemplate('{basename}_v{version:04d}{ext}',
            ...     path='/path/to/shot',
            ...     namespace={'basename': 'Awesome_Shot', 'ext': '.mb'},
            ... )
            >>> tpl.format(version=123, ext='.ma')
            '/path/to/shot/Awesome_Shot_v0123.ma'
            
        """
        
        namespace = dict(self_.namespace or {})
        namespace.update(kwargs)
        rel_path = self_.template.format(**namespace)
        return os.path.join(self_.path, rel_path)
    
    def match(self, path):
        """Match a path, returning a ``dict`` of fields if the input matched.
        
        Will match relative to the path passed to the constructor.
        
        :param str input: The name or path to attempt to parse.
        :returns: ``dict`` or ``None``.
        
        ::
        
            >>> tpl = BoundTemplate('{basename}_v{version:04d}{ext}',
            ...     path='/path/to/shot',
            )
            >>> tpl.match('/path/to/shot/Awesome_Shot_v0123.ma')
            {'basename': 'Awesome_Shot', 'version': 123, 'ext': '.ma'}
        
        """
        rel_path = os.path.relpath(path, self.path)
        return self.template.match(rel_path)
        













            
    
        