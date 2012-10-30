import re


class Template(object):
    
    """A template for formatting or parsing file paths and names."""
    
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
    
    def __init__(self, format_string):
        self.format_string = format_string
        self._compile_reverse()
    
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
        return self.format_string.format(**kwargs)
    
    def match(self, input):
        m = self.reverse_re.match(input)
        if not m:
            return
        
        res = {}
        
        for field, parser, value in zip(self.fields, self.field_parsers, m.groups()):
            if parser is None:
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
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
            
    
        