import os

import yaml

from .structure import Structure


class Schema(object):
    
    """A template of file structures to create for Shotgun entities.

    A Schema is a directed acyclic graph of file structure templates.
    A schema is merged with a :class:`.Context` graph to create a concrete
    :class:`.Structure` graph.

    Schemas are defined as a set of template directories and YAML files to
    describe them. They are located in the "schemas" directory within the
    ``sgfs`` package. 


    """

    def __init__(self, name=None, entity_type='Project', config_name=None):
        
        #: The name of the schema, taken from :envvar:`SGFS_SCHEMA`.
        name = name or os.environ.get('SGFS_SCHEMA')
        if not name:
            raise ValueError('schema must be given or set by $SGFS_SCHEMA')

        #: The path to the root of the schema.
        root = os.path.abspath(os.path.join(
            __file__, 
            os.pardir,
            'schemas',
            name,
        ))
        if not os.path.exists(root):
            raise ValueError('schema %r does not exist' % name)
        
        self.root = root
        self.entity_type = entity_type
        self.config_name = config_name or entity_type + '.yml'
        self.config = yaml.load(open(os.path.join(root, self.config_name)).read())
        
        # Set some defaults on the config.
        self.config.setdefault('type', 'entity')
        default_template = os.path.join(root, os.path.splitext(self.config_name)[0])
        if os.path.exists(default_template):
            self.config.setdefault('template', default_template)
        
        # Load all the children.
        self.children = {}
        for child_type, child_config_name in self.config.get('children', {}).iteritems():
            self.children[child_type] = Schema(root, child_type, child_config_name)
    
    def __repr__(self):
        return '<Schema %s:%s at 0x%x>' % (os.path.basename(self.root), self.entity_type, id(self))
    
    def pprint(self, depth=0):
        """Print a representation of the graph.

        ::

            >>> schema = Schema('v1')
            >>> schema.pprint()
            Project "Project.yml" {
                Asset "Asset.yml" {
                    Task "Task.yml"
                }
                Sequence "Sequence.yml" {
                    Shot "Shot.yml" {
                        Task "Task.yml"
                    }
                }
            }

        """
        print '%s%s "%s"' % (
            '\t' * depth,
            self.entity_type,
            self.config_name,
        ),
        if not self.children:
            print
            return
        
        print '{'
        for type_, child in sorted(self.children.iteritems()):
            child.pprint(depth + 1)
        print '\t' * depth + '}'
    
    def build_structure(self, sgfs, context, root=None):
        """Render this schema into a :class:`.Structure`."""

        # Make sure that this schema matches the context we have been asked to
        # create a structure for.
        if self.entity_type != context.entity['type']:
            raise ValueError('context entity type does not match; %r != %r' % (
                self.entity_type, context.entity['type']
            ))
        
        if root is None:
            root = sgfs.root
        
        # Create the structure node for this entity.
        structure = Structure.from_context(context, self.config.copy(), root)
        if not structure:
            return
        
        # Create all of the Context's child nodes as well.
        for child_context in context.children:
            child_type = child_context.entity['type']
            if child_type in self.children:
                child_structure = self.children[child_type].build_structure(sgfs, child_context, structure.path)
                if child_structure:
                    structure.children.append(child_structure)
        
        return structure

