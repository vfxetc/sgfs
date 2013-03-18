import ast
import os
import re


class MatchResult(dict):
    """Match results from :meth:`.Template.match`.
    
    This object will have roughly the same structure as that
    which was used to :meth:`~.Template.format` the path, however attribute
    and item access has been rolled together.
    You may access values by either
    attribute or item access.
    
    This means that you cannot distinguish between
    attributes and items of the same name.
    
    Since we have not had this problem
    in practise, it has not been addressed, but for future compatibility be
    sure to access the result values in the same way that you would from the
    original objects passed to :meth:`.Template.format`.
    
    We have prioritized item access, so any attributes will be shadowed by
    attributes of the :class:`dict` class.
    
    """
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


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
    def format(self_, *args, **kwargs):
        """Format the template with the given kwargs.
        
        :param dict kwargs: Values to substitute into the pattern.
        :raises KeyError: When there is a missing value.
        
        ::
        
            >>> tpl = Template('{basename}_v{version:04d}{ext}')
            >>> tpl.format(basename='Awesome_Shot', version=123, ext='.ma')
            'Awesome_Shot_v0123.ma'
            
        """
        
        data = {}
        for arg in args:
            data.update(arg)
        data.update(kwargs)
        
        try:
            return self_.format_string.format(**data)
        except (AttributeError, KeyError) as e:
            raise type(e)('%s in %r' % (e.args[0], self_.format_string))
    
    def match(self, input):
        """Match a name or path, returning a ``dict`` of fields if the input matched.
        
        :param str input: The name or path to attempt to parse.
        :returns: :class:`.MatchResult` or ``None``.
        
        ::
        
            >>> tpl = Template('{basename}_v{version:04d}{ext}')
            >>> m = tpl.match('Awesome_Shot_v0123.ma')
            >>> m
            {'basename': 'Awesome_Shot', 'version': 123, 'ext': '.ma'}
            
            >>> m['basename']
            'Awesome_Shot'
            
            >>> m.version
            123
        
        .. warning:: See :class:`.MatchResult` for some caveats.
        
        """
        m = self._reverse_re.match(input)
        if not m:
            return
        
        res = MatchResult()
        
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
                to_store = to_store.setdefault(parts.pop(0), MatchResult())
            to_store[parts[0]] = value
        
        return res


class BoundTemplate(object):
    """A :class:`.Template` relative to a :class:`.Structure` in the file
    system, with default values for entities in the context of that structure.

    
    This behaves like a normal template, except it will
    :meth:`~.BoundTemplate.format` and :meth:`~.BoundTemplate.match` relative to
    a given path. It will also have a namespace including the entities in the
    context in which the sutrcture was created. For example, a template located
    in a ``Task`` schema config will have access to ``Task`` (also via
    ``self``) and ``Shot`` or ``Asset``, and all other entities up the chain to
    the ``Project``.
    
    :param str format: A format string, or a :class:`Template` instance.
    :param structure: The :class:`.Structure` to bind to.
    
    """
    
    
    def __init__(self, template, structure):
        if isinstance(template, basestring):
            template = Template(template)
        
        self.template = template
        self.structure = structure
    
    def __repr__(self):
        return '<BoundTemplate %r on %r>' % (os.path.join(self.path, self.template.format_string), self.entity)
    
    @property
    def path(self):
        """The path of the bound :attr:`.structure`."""
        return self.structure.path
    
    @property
    def context(self):
        """The :class:`.Context` of the bound :class:`.Structure`."""
        return self.structure.context
    
    @property
    def entity(self):
        """The :class:`~sgsession:sgsession.entity.Entity` of the bound :class:`.Context`."""
        return self.structure.context.entity
    
    # `self_` so that `self` can be passed via kwargs.
    def format(self_, *args, **kwargs):
        """Format the template as a path with the given kwargs.
        
        The underlying template will be joined to the ``path`` of the bound
        :class:`.Structure`, and the path will be normalized.
        
        Also uses entities from the bound :class:`.Context`, and values from
        the bound :attr:`.Schema.config`, but priority is
        given to values in ``**kwargs``.
        
        ::
        
            >>> # Get a Structure with path '/path/to/shot'
            >>> tpl = BoundTemplate('{Shot[code]}_v{version:04d}{ext}', structure)
            >>> tpl.format(version=123, ext='.mb')
            '/path/to/shot/Awesome_Shot_v0123.ma'
            
        """
        
        namespace = self_.context.build_eval_namespace(self_.structure.config)
        for arg in args:
            namespace.update(arg)
        namespace.update(kwargs)
        rel_path = self_.template.format(namespace)
        return os.path.normpath(os.path.join(self_.path, rel_path))
    
    def match(self, path):
        """Match a path, returning a ``dict`` of fields if the input matched.
        
        Will match relative to the ``path`` of the bound :class:`.Structure`.
        
        :param str input: The name or path to attempt to parse.
        :returns: :class:`.MatchResult` or ``None``.
                
        ::
        
            >>> # Get a Structure with path '/path/to/shot'
            >>> tpl = BoundTemplate('{Shot[code]}_v{version:04d}{ext}', structure)
            >>> tpl.match('/path/to/shot/Awesome_Shot_v0123.ma')
            {'Shot': {'code': 'Awesome_Shot'}, 'version': 123, 'ext': '.ma'}
        
        .. warning:: See :class:`.MatchResult` for some caveats.
        
        """
        rel_path = os.path.relpath(path, self.path)
        return self.template.match(rel_path)

