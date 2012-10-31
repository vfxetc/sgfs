import ast
import os
import re


class Template(object):
    
    """A template for formatting or parsing file paths.
    
    While they may be used independantly, templates are normally sourced via
    :func:`sgfs.sgfs.SGFS.find_template`, and so they will be relative to the real disk
    location of the coresponding :class:`~sgfs.structure.Structure` node. They
    will also have a namespace including the entities above that node in the
    context in which the sutrcture was created.
    
    For example, a template located in a ``Task`` schema config will have access
    to ``Task`` (also via ``self``) and ``Shot`` or ``Asset``, and all other
    entities up the chain to the ``Project``.
    
    :param str format_string: A :ref:`Python format string <python:formatstrings>`
        for a relative path.
    :param str path: The path from which the format string is relative to.
    :param dict namespace: The base values for the formatting operation.
    
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
    
    def __init__(self, format_string, path=None, namespace=None):
        self.format_string = format_string
        self.path = path
        self.namespace = namespace or {}
        self._compile_reverse()
    
    def __repr__(self):
        return '<Template %r at %r>' % (self.format_string, self.path)
    
    def _compile_reverse(self):
        self.fields = []
        self.field_parsers = []
        self.reverse_pattern = re.sub(r'{([^}]*)}', self._compile_reverse_sub, self.format_string)
        self.reverse_re = re.compile(self.reverse_pattern +'$')
    
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
        self.field_parsers.append(parser)
        return '(%s)' % (pattern)
    
    def format(self, **kwargs):
        relative = self.format_relative(**kwargs)
        if self.path:
            return os.path.join(self.path, relative)
        return relative
        
    def format_relative(self, **kwargs):
        namespace = dict(self.namespace)
        namespace.update(kwargs)
        return os.path.normpath(self.format_string.format(**namespace))
    
    def match(self, input):
        m = self.reverse_re.match(input)
        if not m:
            return
        
        res = {}
        
        for field, parser, value in zip(self.fields, self.field_parsers, m.groups()):
            
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
            
    
        