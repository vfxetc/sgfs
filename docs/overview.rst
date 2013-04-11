Overview
========

.. _tags:

Tags
----

Once folders have been created, the mapping bettween those folders and the Shotgun entities from which they originated are maintained via "tags". These tags exist within ``.sgfs.yml`` files within the top-level of the directory that corresponds to the given entity.

Location
^^^^^^^^

With the WesternX structure, the project tree (including tags) looks roughly like::

    The_Awesome_Project/
        .sgfs.yml # Project tag.
        .sgfs-cache.sqlite # Reverse cache.
        SEQ/
            AA/
                .sgfs.yml # "AA" Sequence tag.
                AA_001_001/
                    .sgfs.yml # "AA_001_001" Shot tag.
                    Light/
                        .sgfs.yml # Tags for Tasks with step code "Light".
        Assets/
            Character/
                Cow/
                    .sgfs.yml # "Cow" Asset tag.
                    Model/
                        .sgfs.yml # "Tags for Tasks with step code "Model".

Contents
^^^^^^^^

The ``.sgfs.yml`` files are `YAML <http://www.yaml.org/>`_ documents containing a logical document for each tag. Those documents are mappings including a timestamp, the entity for that tag, and other arbitrary metadata. The entities have been dumped with all the information that was known about their lineage up to the project. For example, a tag for a shot may look like::

    ---
    created_at: 2012-10-23 18:27:24.312373
    entity:
        code: RG_006_001
        id: 5847
        project:
            id: 70
            name: Super Buddies
            type: Project
            updated_at: 2012-09-17 22:40:23
        sg_sequence:
            code: RG
            id: 107
            name: RG
            project:
                id: 70
                type: Project
            type: Sequence
            updated_at: 2012-10-23 19:29:58
        type: Shot
        updated_at: 2012-10-24 01:31:37


Rules
^^^^^

Usage of tags follows a few general rules:

- tags must contain an entity;
- tags may optionally contain metadata in addition to that entity;
- a directory may be tagged multiple times with different entities;
- if a directory is tagged more than once with the same entity, only the most recent tag will be returned and older metadata will be lost (although older Shotgun data will be merged into the session if not outdated).


Everything Else
---------------


.. todo:: Document thoroughly:

    - :class:`~sgfs.context.Context` overview
    - :class:`~sgfs.schema.Schema` overview, configuration, and API
    - :class:`~sgfs.structure.Structure` overview and API
    - :class:`~sgfs.cache.PathCache` overview and API