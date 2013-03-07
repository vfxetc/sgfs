Picker
=======

- Rename module:
    - sgfs.model_view (perhaps too generic)
    - sgfs.entity_picker
    - sgfs.state_picker (this is how it is implemented)

- Preview not hidden on Maya 2011.

- Filesystem nodes.

- Sort order or sort-key that is seperate from the display data
- Auto-select, to automatically jump to the latest version. Takes effect
  when a node is added, has "select" in `view_data`, and its parent is
  already selected

- Node to wrap around other nodes to get a union of them. Then we can
  easily add a union of PublishEvent and WorkFiles

- 

Create Structure
=================

- Set better permissions, including owner/group/perms from config.
    - Sticky bit on directory will go a long way in our setup.
    - Don't be recursive about the configuration; everything that isn't default
      permissions should be set explicitly.


Templates
=========

- Patterns in template names to allow for maya_*_publish template.


Work Namer (aka SceneName)
==========================

- sgfs.scene_name warnings should collect in a list and be displayed to
  the user by the UI, optionally.


Work Picker (aka product_select)
================================

- Should this be changed to the sgfs.state_picker?

Other
=====


- Refactor scene_name so that it can have parts of it set relatively
  easily
    - call it sgfs.work_area, and LEAVE THE OLD ONE so that I break less things
    - perhaps work with SGFS templates?
    - "Options" toggle to hide the sub-directory
    - I haven't ever seen people set the entity or step, so push them into
      the hidden settings


- Rename a few things: scene_name and product_select:
    - both of these things work with arbitrary "products", which are files
      that are associated with Shotgun Tasks:
        - sgfs.product_name.ProductName
        - sgfs.product_selector.ProductSelectorLayout
    - products are things that are the results of work, so maybe workfile:
        - sgfs.workfile_name or work_name or work_namer
        - sgfs.workfile_pick or work_pick or work_picker
        - sgfs.path_picker (this is how it is implemented)


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
    
    