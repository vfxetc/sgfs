Picker
=======

- Preview not hidden on Maya 2011.

- Fix sizeHint on columns, since they are far too tall.
- Filesystem nodes.




Create Structure
=================

- Set better permissions, including owner/group/perms from config.
    - Sticky bit on directory will go a long way in our setup.
    - Don't be recursive about the configuration; everything that isn't default
      permissions should be set explicitly.


Templates
=========

- Patterns in template names to allow for maya_*_publish template.


Other
=====

- Rename SceneName
    - FileNameBuilder
    
- Rename product_select.
- ProductSelector(allow_custom=False)

- Cache lookups by code/name as well as by ID.
- Get setup.py including the schema (via a MANIFEST?).
- Rename some SGFS methods:
    Clumsy or too explicit:
        - get_directory_entity_tags
        - tag_directory_with_entity
    Unify:
        - path_for_entity
            BUT, this is the path for the specific given entity, where the
            "from"s' products derive from that path. This is a 1-to-1
            relationship.
        - entities_from_path
            BUT, "from_path" implies the products are derived from the path, not
            from the contents of the directory at that path
        - context_from_path
            BUT, same as entities_from_path
        - entities_in_directory (recursive version of above)
            BUT, "in" implies we are travelling deeper into a diretory, while
            the others travel up the heirarchy.
        - context_from_entities
            This may be the only legitimate one. Perhaps context_for_entities,
            BUT this is also a derived product.
    
    