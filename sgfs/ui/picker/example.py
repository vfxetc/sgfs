import itertools
import functools
import optparse

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

from .model import *
from .view import *
from .comboboxview import *
from .utils import *
from .nodes.sgfs import *
from .nodes.shotgun import *

def main():
    
    import sgfs.commands.utils as command_utils
    
    
    optparser = optparse.OptionParser()
    optparser.add_option('-c', '--combobox', action="store_true", dest="combobox")
    optparser.add_option('-r', '--root', dest='root')
    
    opts, args = optparser.parse_args()
    
    global model, view, dialog
    
    sgfs = SGFS()
    
    
    if opts.root:
        root = command_utils.parse_spec(sgfs, opts.root.split())
        model = Model(state_from_entity(sgfs.session.get(root['type'], root['id'])), sgfs=sgfs)
    
    else:
        model = Model(sgfs=sgfs)


    # entity = model.sgfs.session.get('Task', 43897)
    # entities = []
    # while entity:
    #     entities.append(entity)
    #     entity = entity.parent()
    # print 'ENTITY', entities
    # model.register_node_type(functools.partial(ShotgunEntities, entities=entities))


    # model.register_node_type(SGFSRoots)
    # model.register_node_type(ShotgunPublishStream)
    # model.register_node_type(functools.partial(ShotgunQuery, entity_types=('EventLogEntry', 'ActionMenuItem', 'Step', 'PublishEvent', 'Asset', 'Sequence', 'Shot', 'Task', 'Version', 'Tool', 'Ticket', 'Project', 'HumanUser')))
    model.register_node_type(functools.partial(ShotgunQuery, entity_types=('Sequence', 'Shot', 'Project')))

    if opts.combobox:
        view = ComboBoxView()
    else:
        view = ColumnView()
    
    view.setModel(model)

    type_ = None
    id_ = None
    
    if args:
        init = command_utils.parse_spec(model.sgfs, args)
        type_ = init.get('type')
        id_ = init.get('id')
        print type_, id_
    
    if type_ and id_:
        entity = model.sgfs.session.get(type_, id_)
        init_state = state_from_entity(entity)

        index = model.index_from_state(init_state)
        if index:
            view.setCurrentIndex(index)
        else:
            print 'Could not get index for initial state.'

    if not opts.combobox:
        view.setMinimumWidth(800)
        view.setFixedHeight(400)
        view.setColumnWidths([198] + [200] * 10)
        view.setPreviewVisible(False)

    dialog = QtGui.QDialog()
    dialog.setWindowTitle(sys.argv[0])
    dialog.setLayout(QtGui.QVBoxLayout())
    dialog.layout().addWidget(view)
    
    dialog.show()
    dialog.raise_()

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    
    import gc
    # gc.set_debug(gc.DEBUG_LEAK)
    
    main()
    exit(app.exec_())