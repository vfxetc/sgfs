from sgfs import SGFS

from sgactions.utils import notify, progress, alert


def run_create(**kwargs):
    _run(False, **kwargs)

def run_preview(**kwargs):
    _run(True, **kwargs)

def _run(dry_run, entity_type, selected_ids, **kwargs):
    
    title='Preview Folders' if dry_run else 'Creating Folders'
    verb = 'previewing' if dry_run else 'creating'

    progress(message=('Previewing' if dry_run else 'Creating') + ' folders for %s %ss; please wait...' % (len(selected_ids), entity_type))

    sgfs = SGFS()
    
    entities = sgfs.session.merge([dict(type=entity_type, id=id_) for id_ in selected_ids])
    heirarchy = sgfs.session.fetch_heirarchy(entities)
    sgfs.session.fetch_core(heirarchy)
    
    command_log = sgfs.create_structure(entities, dry_run=dry_run)
    
    if command_log:
        details = '\n'.join(command_log)
        if dry_run:
            alert(title='Folder Preview', message=details)
        else:
            notify(
                message='Created folders for %s %ss.' % (len(selected_ids), entity_type),
                details=details,
            )
    else:
        notify(message='Folders are already up to date.')

