Overview
========

.. _tags:

Tags
----

Once folders have been created, the mapping between those folders and the Shotgun entities from which they originated are maintained via **tags**. These tags exist within ``.sgfs.yml`` files within the top-level of the directory that corresponds to the given entity.

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



.. _path_cache:

The Path Cache
--------------

While :ref:`tags <tags>` create a link from directories to their corresponding entities, the **path cache** maintains the links from entities to directories in which they are tagged.

The path cache is implemented as a `sqlite3 <http://www.sqlite.org/>`_ database located at ``.sgfs/cache.sqlite`` within each project, and accessible via the :class:`.PathCache` API.

Since the data in the path cache and tags is redundant, the path cache should be treated as a derivative of the tags and may be reconstructed from the tags at any time via the :ref:`sgfs_relink` command.



Caveats or Known Issues
-----------------------

- Projects must be tagged manually in order for other tools to be able to create structures within them (by default). This is partially a technical restriction (for the creation of the :ref:`path cache <path_cache>`, but also for safety. Manual tagging is done via the :ref:`sgfs_tag` command::

    sgfs-tag Project 1234 path/to/project



Contexts, Schemas, and Structures
---------------------------------


The :class:`.Context`, :class:`.Schema`, and :class:`.Structure` are three different (but related) directed acyclic graphs used in the construction of file structures on disk.

A :class:`.Context` represents a set of Shotgun entities and their relationships.

A :class:`.Schema` represents a template for file structures, and is defined via template structures and YAML files describing them.

A :class:`.Structure` is the specific directories and files that should exist for a set of entities, and allows for creation or inspection of those structures. It is created by rendering Schema for a given Context.
