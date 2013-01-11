from __future__ import absolute_import

# All imports should be in a function so that they do not polute the global namespace.


def standard_setup():
    """Non-standalone user setup."""
    
    import traceback
    import os
    
    import nuke

    import metatools.imports
    import sgfs.nuke.menu

    def callback():
        try:
            metatools.imports.autoreload(sgfs.nuke.menu)
            sgfs.nuke.menu.build_for_path(nuke.root().name())
        except Exception:
            traceback.print_exc()

    nuke.addOnScriptSave(callback)
    nuke.addOnScriptLoad(callback)

    try:
        sgfs.nuke.menu.build_for_path(os.getcwd())
    except Exception:
        traceback.print_exc()



# Block from running the production init if the dev one already ran.
if not globals().get('__sgfs_menu__'):
    __sgfs_menu__ = True
    standard_setup()


# Cleanup the namespace.
del standard_setup
