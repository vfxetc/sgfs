Command-line Tools
==================

A number of command line tools have been created to deal with common situations. When asked to specify an entity to work on, they will generally accept the following forms:

- a path (e.g. ``.`` or ``SEQ/GB/GB_001_001``);
- an entity type and ID (e.g. ``shot 1234``);
- a sequence code (e.g. ``pv`` or ``GB``);
- a shot code (e.g. ``gb_001`` or ``PV_007_002``);
- nothing, and it will use the current working directory.

.. todo:: The parser will be made to accept task names, asset names, and a few more things.


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

sgfs-tag
^^^^^^^^

.. todo:: Document this.


sgfs-rebuild-cache
^^^^^^^^^^^^^^^^^^

.. todo:: Document this.
