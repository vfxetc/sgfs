Command-line Tools
==================

A number of command line tools have been created to deal with common situations. When asked to specify an entity to work on, they will generally accept the following forms:

- a path (e.g. ``.`` or ``SEQ/GB/GB_001_001``);
- an entity type and ID (e.g. ``shot 1234``);
- a sequence code (e.g. ``pv`` or ``GB``);
- a shot code (e.g. ``gb_001`` or ``PV_007_002``);
- nothing, and it will use the current working directory.


Basics
------

sgfs-cd
^^^^^^^

Move your terminal to the given entity.


sgfs-open
^^^^^^^^^

Open the folder for the given entity.


sgfs-shotgun
^^^^^^^^^^^^

Open the Shotgun page for the given entity.


Tags and Caches
---------------

.. _sgfs_tag:

sgfs-tag
^^^^^^^^

::

    $ sgfs-tag <entity_type> <entity_id> <path_to_folder>


.. _sgfs_update:

sgfs-update
^^^^^^^^^^^

When operating with paths instead of entities, SGFS uses entity fields cached in the folder tags. We tend to only cache fields that rarely change, but sometimes, e.g. when a shot or sequence is renamed, those fields need to be updated.

This command will rewrite the tags with up-to-date data::

    Update the cached tag data for the current folder.
    $ sgfs-update .
    
    Update the cached tag data for every entity in the current folder.
    $ sgfs-update -r .


.. _sgfs_relink:

sgfs-relink
^^^^^^^^^^^

When a folder is moved on disk, the one of the two links between Shotgun and that folder is broken, and you will not be able to get a path from an entity any more.

The links must be recreated with this tool::

    Relink the entity for the current folder.
    $ sgfs-relink .
    
    Relink all entities under this folder.
    $ sgfs-relink -r .

Since this is a common situation after renaming shots or sequences, this tool can automatically call the updater on paths that were relinked::

    $ sgfs-relink -r --update .
