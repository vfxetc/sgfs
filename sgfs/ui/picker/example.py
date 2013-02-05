import sys
import functools
import optparse

from PyQt4 import QtCore, QtGui
Qt = QtCore.Qt

from sgfs import SGFS

from sgfs.ui.picker.model import Model
from sgfs.ui.picker.view import ColumnView
from sgfs.ui.picker.comboboxview import ComboBoxView
from sgfs.ui.picker.utils import state_from_entity
from sgfs.ui.picker.nodes.shotgun import ShotgunPublishStream, ShotgunQuery
from sgfs.ui.picker.nodes.sgfs import TemplateGlobPicker


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
    # model.register_node_type(functools.partial(ShotgunPublishStream, publish_types=['maya_scene']))
    # model.register_node_type(functools.partial(ShotgunQuery, entity_types=('EventLogEntry', 'ActionMenuItem', 'Step', 'PublishEvent', 'Asset', 'Sequence', 'Shot', 'Task', 'Version', 'Tool', 'Ticket', 'Project', 'HumanUser')))
    model.register_node_type(functools.partial(ShotgunQuery, entity_types=('Asset', 'Sequence', 'Shot', 'Project', 'Task')))

    model.register_node_type(functools.partial(TemplateGlobPicker, entity_types=('Task', ), template='nuke_scripts_dir', glob='*.nk'))

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

    view.setMinimumWidth(800)

    if not opts.combobox:
        view.setMaximumHeight(400)
        view.setPreviewVisible(False)
        view.setColumnWidths([1] * 10)


    dialog = QtGui.QDialog()
    dialog.setWindowTitle(sys.argv[0])
    dialog.setLayout(QtGui.QHBoxLayout())
    dialog.layout().addWidget(view)
    dialog.layout().addStretch()

    dialog.show()
    dialog.raise_()

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    
    main()
    exit(app.exec_())

