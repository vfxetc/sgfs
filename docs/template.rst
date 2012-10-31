Templates
=========

.. autoclass:: sgfs.template.Template

.. automethod:: sgfs.template.Template.format
.. automethod:: sgfs.template.Template.match

Bound Templates
---------------

.. autoclass:: sgfs.template.BoundTemplate

.. attribute:: BoundTemplate.template

    The :class:`.Template` that is bound.

.. attribute:: BoundTemplate.structure

    The :class:`.Structure` that the :attr:`~.BoundTemplate.template` is bound
    to.

.. autoattribute:: sgfs.template.BoundTemplate.context
.. autoattribute:: sgfs.template.BoundTemplate.entity
.. autoattribute:: sgfs.template.BoundTemplate.path

.. automethod:: sgfs.template.BoundTemplate.format
.. automethod:: sgfs.template.BoundTemplate.match


Match Results
-------------

.. autoclass:: sgfs.template.MatchResult
    :members:
