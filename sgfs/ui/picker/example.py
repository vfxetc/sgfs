from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from .model import *
from .view import *
from .utils import *
from .nodes.sgfs import *
from .nodes.shotgun import *


app = QtGui.QApplication(sys.argv)
    
view_class = ColumnView
    
if False:
    model = Model(state_from_entity(sgfs.session.get('Project', 74)))
else:
    model = Model()
    
model.node_types.append(SGFSRoots)
# model.node_types.append(ShotgunProjectTopLevel)
# 
# if False:
#     model.node_types.append(ShotgunSteps) # Must be before ShotgunTasks
# 
# model.node_types.append(ShotgunTasks)
    
model.node_types.append(ShotgunQuery.specialize(('Asset', 'Sequence', 'Shot', 'Task', 'PublishEvent')))

# model.node_types.append(ShotgunQuery.for_entity_type('Tool'        , ('Project', 'project'), '{code}', fields=['code']))
# model.node_types.append(ShotgunQuery.for_entity_type('Ticket'        , ('Tool', 'sg_tool'), '{title}', fields=['title']))
    
# model.node_types.append(ShotgunQuery.for_entity_type('Sequence'    , ('Project' , 'project'    ), '{code}', group_format='Sequence'))
# model.node_types.append(ShotgunQuery.for_entity_type('Asset'       , ('Project' , 'project'    ), '{code}', group_format=('Asset', '{Asset[sg_asset_type]}')))
# model.node_types.append(ShotgunQuery.for_entity_type('Shot'        , ('Sequence', 'sg_sequence'), '{code}'))
#model.node_types.append(ShotgunQuery.for_entity_type('PublishEvent', ('Task'    , 'sg_link'    ), 'v{sg_version:04d}', group_format=('{PublishEvent[sg_type]}', '{PublishEvent[code]}')))


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

    print 'init_state', init_state
    print
    
    index = model.set_initial_state(init_state)

    view = view_class()
    view.setModel(model)
    if index:
        # debug('selecting %r -> %r', index, model.node_from_index(index))
        view.setCurrentIndex(index)

else:
        
    print 'no entity specified'
        
    view = view_class()
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