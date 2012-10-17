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
    
    overview
    
    sgfs
    context
    cache


.. todo:: Document thoroughly:

   
    - ``.sgfs.yml`` tags
    - reverse cache
    - ``SGFS`` API
    - ``Context`` API
    - ``PathCache`` API

.. graphviz:: /_graphs/linear_context/main.0.dot
.. graphviz:: /_graphs/task_forked_context/main.0.dot


Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

