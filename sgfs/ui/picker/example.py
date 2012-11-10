import itertools
import functools

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

from .model import *
from .view import *
from .utils import *
from .nodes.sgfs import *
from .nodes.shotgun import *

def main():
    
    global model, view, dialog
    
    sgfs = SGFS()
    if False:
        model = Model(state_from_entity(sgfs.session.get('Project', 66)), sgfs=sgfs)
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
    model.register_node_type(functools.partial(ShotgunQuery, entity_types=('EventLogEntry', 'ActionMenuItem', 'Step', 'PublishEvent', 'Asset', 'Sequence', 'Shot', 'Task', 'Version', 'Tool', 'Ticket', 'Project', 'HumanUser')))


    view = ColumnView()

    type_ = None
    id_ = None


    if len(sys.argv) > 1:
    
        import sgfs.commands.utils as command_utils
        data = command_utils.parse_spec(model.sgfs, sys.argv[1:])
        
        type_ = data.get('type')
        id_ = data.get('id')
    
    if type_ and id_:
        
        print type_, id_
        entity = model.sgfs.session.get(type_, id_)
        
        init_state = {}
        while entity and entity['type'] not in init_state:
            init_state[entity['type']] = entity
            entity = entity.parent()

        print 'Initial state:'
        pprint.pprint(init_state)
        print
    
    
        view.setModel(model)
    
        index = model.index_from_state(init_state)
        if index:
            view.setCurrentIndex(index)
        else:
            print 'Could not get index for initial state!'

    else:
        
        print 'no entity specified'
        
        view.setModel(model)
    
    # view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    view.setFixedWidth(800)
    view.setFixedHeight(400)
    view.setColumnWidths([198] + [200] * 10) # To be sure that the width is 2 more.
    # view.setResizeGripsVisible(False)

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