import os
import sys
import time
import thread
import subprocess

from PyQt4 import QtGui


_debug_start = time.time()
_debug_last = _debug_start
_debug_thread_ids = {}
def debug(msg, *args):
    global _debug_last
    if args:
        msg = msg % args
    ident = _debug_thread_ids.setdefault(thread.get_ident(), len(_debug_thread_ids))
    current_time = time.time()
    sys.stdout.write('# %8.3f (%8.3f) %3d %s\n' % ((current_time - _debug_start) * 1000, (current_time - _debug_last) * 1000, ident, msg))
    sys.stdout.flush()
    _debug_last = current_time


def state_from_entity(entity):
    state = {
        'self': entity,
    }
    while entity and entity['type'] not in state:
        state[entity['type']] = entity
        entity = entity.parent()
    return state


_icons_by_name = {}
def icon(name, as_icon=False):
    
    try:
        icon = _icons_by_name[name]
    except KeyError:
    
        path = os.path.abspath(os.path.join(__file__, 
            '..', '..', '..', 'art', 'icons',
            name + '.png'
        ))
        if os.path.exists(path):
            icon = QtGui.QPixmap(path)
        else:
            icon = None
    
        _icons_by_name[name] = icon
    
    if as_icon:
        icon = QtGui.QIcon(icon)
    
    return icon

def call_open(x):
    if sys.platform.startswith('darwin'):
        subprocess.call(['open', x])
    else:
        subprocess.call(['xdg-open', x])

