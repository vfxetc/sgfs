import re


class Template(object):
    
    """A template for formatting or parsing file paths and names."""
    
    _format_type_to_re = {
        'b': (r'[-+]?(?:0b)?[01]+', int),
        'c': (r'.+', str),
        'd': (r'[-+]?\d+', int),
        'e': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'E': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'f': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'F': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'g': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'G': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', float),
        'n': (r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', None),
        'o': (r'[-+]?(?:0o)?[0-7]+', int),
        's': (r'.+', str),
        'x': (r'[-+]?(?:0[xX])?[\dA-Fa-f]+', int),
        'X': (r'[-+]?(?:0[xX])?[\dA-Fa-f]+', int),
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
        self.field_parsers = {}
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
        format_spec = m.group(1) if m else 's'
        m = self._format_type_re.match(format_spec)
        if not m:
            raise ValueError('could not parse format spec %r' % format_spec)
        fill, align, sign, number_prefix, zero_pad, width, comma, precision, type_ = m.groups()
        
        # Get the pattern and parser, and finally return a RE.
        pattern, parser = self._format_type_to_re[type_]
        self.field_parsers[field_name] = parser
        return '(?P<%s>%s)' % (field_name, pattern)
    
    def format(self, **kwargs):
        return self.format_string.format(**kwargs)
    
    def match(self, input):
        m = self.reverse_re.match(input)
        if m:
            return m.groupdict()
    
        