from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from .model import *
from .view import *
from .utils import *
from .nodes.sgfs import *
from .nodes.shotgun import *


app = QtGui.QApplication(sys.argv)
    
    
if False:
    model = Model(state_from_entity(sgfs.session.get('Project', 74)))
else:
    model = Model()

model.register_node_type(SGFSRoots)
model.register_node_type(ShotgunQuery.specialize(('Asset', 'Sequence', 'Shot', 'Task', 'PublishEvent')))
        
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
    
    index = model.set_initial_state(init_state)
    if not index:
        print 'Could not get index for initial state!'
    
    view.setModel(model)
    if index:
        view.setCurrentIndex(index)

else:
        
    print 'no entity specified'
        
    view.setModel(model)
    
# view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
view.setFixedWidth(800)
view.setColumnWidths([200] * 10) # To be sure that the width is 2 more.
# view.setResizeGripsVisible(False)

view.setPreviewVisible(False)

dialog = QtGui.QDialog()
dialog.setWindowTitle(sys.argv[0])
dialog.setLayout(QtGui.QVBoxLayout())
dialog.layout().addWidget(view)
    
dialog.show()
dialog.raise_()

exit(app.exec_())