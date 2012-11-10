Picker
=======

- Fix sizeHint on columns, since they are far too tall.
- Fix segfault on SSL_read on OS X.
- Filesystem nodes.
- __THE_PROCESS_HAS_FORKED_AND_YOU_CANNOT_USE_THIS_COREFOUNDATION_FUNCTIONALITY___YOU_MUST_EXEC__ on errors on OS X

Create Structure
=================

- Set better permissions, including owner/group/perms from config.
    - Sticky bit on directory will go a long way in our setup.

