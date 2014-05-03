.. _known_issues:

Known Issues
============

Most of the issues with SGFS come up with invalid data in the :ref:`tags <tags>` that are placed in the file structure, either due to information changing on Shotgun, or folders being moved/copied.


Missing Links
-------------

Starting a Project
^^^^^^^^^^^^^^^^^^

The folder for a project cannot be created from Shotgun (simply because we have deemed it special). You must manually create it and then tag it via :ref:`sgfs_tag`::

    $ sgfs-tag Project 1234 /Volumes/VFX/Projects/New_Project_Folder

(This example assumes the Shotgun ID of the project's entity is ``1234``.)


Manually Copied Folders
^^^^^^^^^^^^^^^^^^^^^^^

Folders (or parents of folders) linked to a Shotgun entity should not be copied as a template for another structure. If they are relinked (via :ref:`sgfs_relink`) then the copy may override the original as far as Shotgun is concerned.

To fix, delete all ``.sgfs.yml`` files in the duplicate folder::

    $ find $copy -name .sgfs.yml -delete

relink the original::

    $ sgfs-relink -r $original

and then create the folders for the copied entity from Shotgun itself.


Invalid Data
------------

Quite a bit of data is cached in the :ref:`tags <tags>`, although much of it isn't critical. Some of it, however, can lead to some very strange Python exceptions.

Changing the pipeline step, name, or code of a task after the folders have been created has led to some strange exceptions in the past. This is likely due to some of the older tools using these fields as part of some string-based path construction.

Either put the value back to what it was, or use :ref:`sgfs_update` on the folders.



