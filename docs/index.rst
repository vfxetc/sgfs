.. _index:

sgfs
=========

This Python package is a translation layer between `Shotgun <http://www.shotgunsoftware.com/>`_ entities and a file structure on disk. In general, its overarching tasks are to:

- map Shotgun entities to their canonical path on disk;
- map paths on disk to the coresponding Shotgun entities;
- create new structures on disk;
- indentify existing structures on disk for use in above translation.


Contents
--------

.. toctree::
    :maxdepth: 2
    
    sgfs
    context
    ..
        cache


.. todo:: Document thoroughly:

    - :class:`~sgfs.context.Context` overview
    - :class:`~sgfs.schema.Schema` overview, configuration, and API
    - :class:`~sgfs.structure.Structure` overview and API
    - ``.sgfs.yml`` Tag overview
    - :class:`~sgfs.cache.PathCache` overview and API


Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

