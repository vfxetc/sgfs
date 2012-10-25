``sgfs.SGFS`` API
=================

The :class:`~sgfs.sgfs.SGFS` object is the main entrypoint into most functions
of this package. Generally, you construct a ``SGFS`` object and use it to
map entities to paths, get contexts from entities, and create structures. Secondary classes such as :class:`~sgfs.context.Context` are not created directly since they must remain connected to their original ``SGFS``.

.. automodule:: sgfs.sgfs

    .. autoclass:: SGFS


Entities
--------

.. automethod:: sgfs.sgfs.SGFS.entities_from_path
.. automethod:: sgfs.sgfs.SGFS.entities_in_directory
.. automethod:: sgfs.sgfs.SGFS.path_for_entity
    

Contexts
--------
    
.. automethod:: sgfs.sgfs.SGFS.context_from_path
.. automethod:: sgfs.sgfs.SGFS.context_from_entities


Structure
---------

.. automethod:: sgfs.sgfs.SGFS.create_structure
.. automethod:: sgfs.sgfs.SGFS.tag_existing_structure


Tags and Caches
---------------

.. automethod:: sgfs.sgfs.SGFS.tag_directory_with_entity
.. automethod:: sgfs.sgfs.SGFS.get_directory_entity_tags
.. automethod:: sgfs.sgfs.SGFS.entity_tags_in_directory
.. automethod:: sgfs.sgfs.SGFS.path_cache
.. automethod:: sgfs.sgfs.SGFS.rebuild_cache

