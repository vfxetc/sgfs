"""

This is just a stub to redirect a function to its new location. This module
and the containing package can be deleted after a few days.

"""

from metatools.deprecate import renamed_func

from sgfs.maya.workspace import pick_workspace

# The only function that was exporter previously.
run = renamed_func(pick_workspace, 'run', __name__)
