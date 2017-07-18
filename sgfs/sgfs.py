import datetime
import logging
import os

import yaml

from sgsession import Session

from .cache import PathCache
from .context import Context
from .schema import Schema
from . import utils


log = logging.getLogger('sgfs')


class SGFS(object):
    
    """The mapping from Shotgun to the file system.
    
    :param str root: The location of projects on disk. Defaults to ``$SGFS_ROOT``.
    :param session: The :class:`~sgsession.session.Session` to use. Defaults to
        a clean wrapper around the given ``shotgun``.
    :param shotgun: The ``Shotgun`` API to use. Defaults to an automatically
        constructed instance via ``shotgun_api3_registry``.
    
    """
    
    def __init__(self, root=None, session=None, shotgun=None, schema_name=None):
        # This constructor is very light weight, not really doing anything
        # until you ask for it.
        self._root = root
        self._session = session
        self._shotgun = shotgun
        self.schema_name = schema_name
    
    @utils.cached_property
    def root(self):
        # Take the given root, or look it up in the environment.
        root = self._root
        if root is None:
            root = os.environ.get('SGFS_ROOT')
            if root is None:
                raise ValueError('one of root or $SGFS_ROOT must not be None')
        return os.path.abspath(root)
    
    @utils.cached_property
    def session(self):
        # Set the session, building it from a generic Shotgun if nothing was
        # given. This requires a `shotgun_api3_registry.connect()` function.
        if not self._shotgun and not self._session:
            import shotgun_api3_registry
            self._shotgun = shotgun_api3_registry.connect(auto_name_stack_depth=1)
        return self._session or Session(self._shotgun)
        
    @utils.cached_property
    def project_roots(self):
        # Scan the root looking for Project tags in its top level.
        
        # We look at links first so that they get overwritten by data in "real"
        # directories later. This is so that the "real" directory has priority
        # over a link to itself.
        paths = [os.path.join(self.root, name) for name in os.listdir(self.root)]
        paths.sort(key=lambda path: (not os.path.islink(path), path))

        roots = {}
        for path in paths:
            for tag in self.get_directory_entity_tags(path):
                if tag['entity']['type'] == 'Project':
                    roots[tag['entity']] = path
        return roots
    
    def path_cache(self, project):
        """Get a :class:`~sgfs.cache.PathCache` for a given path or entity..
        
        :param project: Either a ``str`` path within a project, or an
            :class:`~sgsession.entity.Entity`.
        :return: A :class:`~sgfs.cache.PathCache` or ``None``.
        
        """
        if isinstance(project, basestring):
            path = os.path.abspath(project)
            for project_root in self.project_roots.itervalues():
                if path.startswith(project_root): # TODO: Do better.
                    return PathCache(self, project_root)
            return
        
        project = project.project()
        project_root = self.project_roots.get(project)
        if project_root is not None:
            return PathCache(self, project_root)
    
    def path_for_entity(self, entity):
        """Get the path on disk for the given entity.
        
        :param entity: An :class:`~sgsession.entity.Entity`
        :return: ``str`` if the entity has a tagged directory, or ``None``.
        
        This only works if the entity has been previously tagged, either by a
        manual process, of if the structure was automatically tagged or created
        by SGFS.
        
        This will also only return a still valid path, since the path cache
        will verify that the returned directory is still tagged with the given
        entity.
        
        E.g.::
        
            >>> # We want a path for this task...
            >>> sgfs.path_for_entity({"type": "Task", "id": 43898})
            '<snip>/SEQ/GC/GC_001_001/Light'
            
            >>> # This one doesn't exist...
            >>> sgfs.path_for_entity({"type": "Task", "id": 123456})
            None
            
        """
        
        entity = self.session.merge(entity)
        
        # Projects are special cased; we should always know the paths to all
        # projects.
        if entity['type'] == 'Project':
            return self.project_roots.get(entity)
        
        # If we already know the project for this entity, then look it up in the
        # project_roots.
        project = entity.project(fetch=False)
        if project is not None:
            path_cache = self.path_cache(project)
            return path_cache.get(entity) if path_cache is not None else None
        
        
        # It should be cheaper to hit the disk to poll all caches than to query
        # the Shotgun server for the project.
        for project in self.project_roots:
            path_cache = self.path_cache(project)
            path = path_cache.get(entity) if path_cache is not None else None
            if path is not None:
                return path

    def _write_directory_tags(self, path, tags, replace=False, backup=True):

        serialized = yaml.dump_all(tags,
            explicit_start=True,
            indent=4,
            default_flow_style=False
        )

        path = os.path.abspath(path)
        tag_path = os.path.join(path, '.sgfs.yml')

        umask = os.umask(0111) # Race condition when threaded?
        try:
            if replace and backup and os.path.exists(tag_path):
                backup_path = os.path.join(path, '.sgfs.%s.yml' % datetime.datetime.utcnow().strftime('%y%m%d.%H%M%S.%f'))
                with open(tag_path, 'r') as rfh, open(backup_path, 'w') as wfh:
                    wfh.write(rfh.read())
            with open(tag_path, 'w' if replace else 'a') as fh:
                fh.write(serialized)
        finally:
            os.umask(umask)

    def _read_directory_tags(self, path):

        path = os.path.abspath(path)

        tag_path = os.path.join(path, '.sgfs.yml')
        if not os.path.exists(tag_path):
            return []
        
        with open(tag_path) as fh:
            return list(yaml.load_all(fh.read()))

    def tag_directory_with_entity(self, path, entity, meta=None, cache=True):
        """Tag a directory with the given entity, and add it to the cache.
        
        This allows us to associate entities with directories, and the reverse.
        
        :param str path: The directory to tag.
        :param entity: The :class:`~sgsession.entity.Entity` to tag it with.
        :param dict meta: Metadata to include in the tag.
        :param bool cache: Add this to the path cache?
        
        """

        path = os.path.abspath(path)

        tag = dict(meta or {})
        tag.update({
            'created_at': datetime.datetime.utcnow(),
            'entity': entity.as_dict(),
            'path': path,
        })
        self._write_directory_tags(path, [tag])
            
        # Add it to the local project roots.
        if entity['type'] == 'Project':
            self.project_roots[entity] = path
        
        # Add to path cache.
        if cache:
            path_cache = self.path_cache(entity.project())
            if path_cache is None:
                raise ValueError('could not get path cache for %r from %r' % (entity.project(), entity))
            path_cache[entity] = path
    
    def get_directory_entity_tags(self, path, allow_duplicates=False, allow_moves=False, merge_into_session=True):
        """Get the tags for the given directory.
        
        The tags will not be returned in any specific order.
        
        :param str path: The directory to get tags for.
        :param bool allow_duplicates: Return all tags, or just the most recent
            for each entity?
        :param bool allow_moves: Return all tags, or just the ones that were
            originally for this directory?
        :param bool merge_into_session: Merge raw data into the session, or
            return the raw data? This implies ``allow_duplicates``.
        :return: ``list`` of ``dict``.
        
        """
        
        path = os.path.abspath(path)

        tags = self._read_directory_tags(path)
        
        # Filter out moved tags.
        if not allow_moves:
            did_warn = False
            unmoved = []
            for tag in tags:
                tagged_path = tag.get('path')
                if tagged_path is not None and path != tagged_path:
                    if not did_warn:
                        print ('Directory at %s was moved from %s' % (path, tagged_path))
                        did_warn = True
                else:
                    unmoved.append(tag)
            tags = unmoved

        # Take the newest version of each tag.
        if not allow_duplicates:
            newest_tags = {}
            for tag in tags:
                entity = tag['entity']
                key = (entity['type'], entity['id'])
                older_tag = newest_tags.get(key)
                if older_tag is None or tag['created_at'] > older_tag['created_at']:
                    newest_tags[key] = tag
            tags = newest_tags.values()

        # Merge all the entity data before filtering out duplicates so that
        # older Shotgun data is still pulled in.
        if merge_into_session:
            for tag in tags:
                tag['entity'] = self.session.merge(tag['entity'], created_at=tag['created_at'])
        
        return tags

    def entities_from_path(self, path, entity_type=None):
        """Get the most specific entities that have been tagged in a parent
        directory of the given path, optionally limited to a given type.
        
        :param str path: The path to find entities for.
        :param str entity_type: The type (or set of types) to look for. None will return
            the first entities found.
        :return: ``tuple`` of :class:`~sgsession.entity.Entity`.
        
        E.g.::
            
            >>> # Get a few lighting tasks.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_001/Light')
            (<Entity Task:43897 at 0x1011b9c0>, <Entity Task:43990 at 0x10112da7>)
            
            >>> # Get the shot.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_001')
            (<Entity Shot:5801 at 0x1011c03d0>,)
            
            >>> # Get the sequence from a shot.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_011', entity_type='Sequence')
            (<Entity Sequence:345 at 0x1011c0948>,)
            
            >>> # Get the shot or asset from a task.
            >>> sgfs.entities_from_path('SEQ/GC/GC_001_011/Light', entity_type=('Shot', 'Asset'))
            (<Entity Shot:5801 at 0x1011c03d0>,)
        
        """
        
        # Convert type into a set of strings, or None.
        if entity_type is not None:
            if isinstance(entity_type, basestring):
                entity_type = set([entity_type])
            else:
                entity_type = set(entity_type)
        
        path = os.path.abspath(path)
        while path and path != '/':
            tags = self.get_directory_entity_tags(path)
            
            # Perform the type filter.
            if entity_type is not None:
                tags = [tag for tag in tags if tag['entity']['type'] in entity_type]
            
            if tags:
                return self.session.merge([x['entity'] for x in tags])
            
            path = os.path.dirname(path)
        return ()
    
    def entities_in_directory(self, path, entity_type=None, load_tags=False, primary_root=None):
        """Iterate across every :class:`~sgsession.entity.Entity` within the
        given directory.
        
        This uses the path cache to avoid actually walking the directory.
        
        :param str path: The path to walk for entities.
        :param str entity_type: Restrict to this type; None returns all.
        :param bool load_tags: Load data cached in tags? None implies automatic.
        :param str primary_root: Any directory within the primary project root.
            None implies the given path.
        :return: Iterator of ``(path, entity)`` tuples.
        
        E.g.::
        
            >>> # Get everything under this shot, including the Shot and Tasks.
            >>> for x in sgfs.entities_in_directory('SEQ/GC/GC_001_001'):
            ...     print x
            ('<snip>/SEQ/GC/GC_001_001', <Entity Shot:5801 at 0x1011bb720>)
            ('<snip>/SEQ/GC/GC_001_001/Anim', <Entity Task:43897 at 0x1011bc0c0>)
            ('<snip>/SEQ/GC/GC_001_001/Light', <Entity Task:43898 at 0x1011bee80>)
            
        """
        path = os.path.abspath(path)
        cache = self.path_cache(primary_root or path)
        if cache is None:
            raise ValueError('No SGFS cache above directory.', path)
        for path, entity in cache.walk_directory(path, entity_type):
            if load_tags or (load_tags is None and len(entity) == 2):
                self.get_directory_entity_tags(path)
            yield path, entity
    
    def entity_tags_in_directory(self, path, **kwargs):
        """Iterate across every tag within the given directory.
        
        This uses the path cache to avoid actually walking the directory.
        
        :param str path: The path to walk for entities.
        :param kwargs: Passed to :func:`~sgfs.sgfs.SGFS.get_directory_entity_tags`.
        :return: Iterator of ``(path, tag_dict)`` tuples.
            
        """
        path = os.path.abspath(path)
        cache = self.path_cache(path)
        visited = set()
        for path, entity in cache.walk_directory(path):
            if path in visited:
                continue
            visited.add(path)
            for tag in self.get_directory_entity_tags(path, **kwargs):
                yield path, tag
    
    def rebuild_cache(self, path, recurse=False, dry_run=False):
        """Rebuilds the cache for a given directory.
        
        This is useful when a tagged directory has been moved, breaking the
        reverse path cache. Rebuilding the cache of that directory using this
        method will reconnect the tags to the path cache.
        
        :param str path: The path to rebuild the cache for.
        :param bool recurse: Should we recursively walk the path, or just look
            at the given one?
        :raises ValueError: when ``path`` is not within a project.
        :returns: ``list`` of changed ``(old_path, found_path, tag)``
        """
        
        root_path = os.path.abspath(path)
        cache = self.path_cache(root_path)
        if cache is None:
            raise ValueError('Could not get path cache from %r' % path)
        
        # Find all the tags.
        to_check = []
        if recurse:
            for path, dir_names, file_names in os.walk(root_path):
                for tag in self.get_directory_entity_tags(path, allow_moves=True):
                    to_check.append((path, tag))
        else:
            for tag in self.get_directory_entity_tags(root_path, allow_moves=True):
                to_check.append((root_path, tag))
        
        # Update them.
        changed = []
        old_tags_by_path = {}
        for path, tag in to_check:

            entity = tag['entity']
            
            # Make sure the old path does not exist and is not
            # tagged the same way. If it is, it was copied, and we should
            # not simply update the cache.
            old_path = cache.get(entity, check_tags=False)
            if old_path is not None and old_path != path:
                
                try:
                    old_tags = old_tags_by_path[old_path] 
                except KeyError:
                    old_tags = old_tags_by_path[old_path] = self.get_directory_entity_tags(old_path, merge_into_session=False)

                was_copied = False
                for old_tag in old_tags:
                    old_entity = old_tag['entity']
                    if old_entity['type'] == entity['type'] and old_entity['id'] == entity['id']:
                        was_copied = True
                        break

                if was_copied:
                    log.warning('%s %s was copied from %s to %s; not updating cache' % (
                        entity['type'], entity['id'], old_path, path,
                    ))
                    continue

                # Update the tags to reflect their new location.
                elif not dry_run:
                    # WARNING: Potential race condition here.
                    raw_tags = self._read_directory_tags(path)
                    did_update_tags = False
                    for raw_tag in raw_tags:
                        if entity.is_same_entity(raw_tag['entity']):
                            raw_tag.setdefault('path_history', []).append({
                                'path': old_path,
                                'updated_at': datetime.datetime.utcnow()
                            })
                            raw_tag['path'] = path
                            did_update_tags = True
                    if did_update_tags:
                        self._write_directory_tags(path, raw_tags, replace=True)
                    else:
                        # I want to know about this...
                        log.error('Tagged paths for %s did not match, but tags not out of date.' % path)


            # Update the path cache.
            if not dry_run:
                cache[tag['entity']] = path

            changed.append((old_path, path, tag))
        
        return changed
    
    def context_from_entities(self, entities):
        """Construct a :class:`~sgfs.context.Context` graph which includes all
        of the given entities.
        
        A ``Project`` must be reachable from every provided entity, and they
        must all reach the same ``Project``.
        
        :param list entities: A ``list`` of :class:`~sgsession.entity.Entity`
            (or bare ``dict``) to get the context of.
        :returns: A :class:`~sgfs.context.Context` rooted at the ``Project``,
            including the given ``entities`` as leafs.
        :raises ValueError: when the project conditions are not satisfied.
        
        E.g.::
            
            >>> sgfs.context_from_entities([{"type": "Task", "id": 43990}]).pprint()
            Project:66 -> Sequence:101 -> Shot:5801 -> Task:43990
        
        """
        
        # Accept a single instance as well.
        if isinstance(entities, dict):
            entities = [entities]
        
        # Assert that they are entities.
        entities = self.session.merge(entities)
        
        if not entities:
            raise ValueError('not given any entities')
        
        # If we don't already have the parent of the entity then populate as
        # much as we can from the cache.
        for entity in entities:
            if entity.parent(fetch=False) and entity.project(fetch=False):
                continue
            path = self.path_for_entity(entity)
            if path:
                self.get_directory_entity_tags(path)
        
        self.session.fetch_heirarchy(entities)
                
        # Assert project conditions.
        projects = [x.project(fetch=False) for x in entities]
        projects = [x for x in projects if x]
                
        if len(projects) != len(entities):
            raise ValueError('given entities do not all have projects')
        if len(set(projects)) != 1:
            raise ValueError('given entities have multiple projects: %s' % (', '.join(str(x['id']) for x in set(projects))))
        
        # Reverse the parent relationships to construct a Context graph
        entity_to_context = {}
        to_resolve = list(entities)
        while to_resolve:
            
            # Grab an entity to resolve, build a context for it if it doesn't
            # already exist, and finish with it if it is the project.
            entity = to_resolve.pop(0)
            try:
                context = entity_to_context[entity]
            except KeyError:
                context = Context(sgfs=self, entity=entity)
                entity_to_context[entity] = context
            
            if entity['type'] == 'Project':
                continue
            
            # Grab the entity's parent, link it up of it already has a context
            # otherwise reschedule them both for resolution.
            parent = entity.parent()
            try:
                parent_context = entity_to_context[parent]
            except KeyError:
                # It would be nice to use a different data structure. Oh well.
                if parent not in to_resolve:
                    to_resolve.append(parent)
                if entity not in to_resolve:
                    to_resolve.append(entity)
            else:
                parent_context.children.append(context)
                context.parent = parent_context
        
        # The project is the root.
        return entity_to_context[projects[0]]
    
    def context_from_path(self, path):
        """Get a :class:`~sgfs.context.Context` with every tagged
        :class:`~sgsession.entity.Entity` in the given path.
        
        :param str path: The path to return a context for.
        
        This walks upwards on the path specified until it finds a directory
        that has been tagged as a ``Project``, and then returns a context
        rooted at that project and containing every entity discovered up to that
        point.
        
        The returned graph may also be non-linear as a directory may be tagged
        more than once. More often than not this will be multiple tasks attached
        to the same entity, and so the fork will exist only in the last step.
        
        E.g.::
        
            >>> ctx = sgfs.context_from_path("SEQ/GC/GC_001_001/Anim")
            >>> ctx
            <Context Project:66 at 0x10183b510>
            >>> ctx.pprint()
            Project:66 -> Sequence:101 -> Shot:5801 {
            	Task:43897
            	Task:43990
            }
        
        An unambiguous (e.g. linear) context may look like:
        
        .. graphviz:: /_graphs/sgfs/context_from_path.0.dot
        
        If there is more than one task in the same path, the context
        may be ambiguous (e.g. non-linear), and may look like:
        
        .. graphviz:: /_graphs/sgfs/context_from_path.1.dot
        
        """
        entities = []
        path = os.path.abspath(path)
        while path and path != '/':
            for tag in self.get_directory_entity_tags(path):
                entities.append(tag['entity'])
                if tag['entity']['type'] == 'Project':
                    return self.context_from_entities(entities)
            path = os.path.dirname(path)
        return
            
    def structure_from_entities(self, entities):
        """Create a :class:`.Structure` graph from the given entities"""
        context = self.context_from_entities(entities)
        return Schema(self.schema_name).build_structure(self, context)
    
    def create_structure(self, entities, **kwargs):
        """Create the structure on disk for the given entities.
        
        :param list entities: The set of :class:`~sgsession.entity.Entity` to
            create structure for.
        :param str schema_name: Which schema to use. Defaults to ``'v1'``
        :param bool dry_run: Don't actually create structure. Defaults to ``False``.
        :param bool verbose: Print out what is going on. Defaults to ``False``.
        :param bool allow_project: Allow creation of projects? Defaults to ``False``.
        :return: A ``list`` of steps taken.
        
        """
        structure = self.structure_from_entities(entities)
        return structure.create(**kwargs)
    
    def tag_existing_structure(self, entities, **kwargs):
        """Tag existing structures without creating new ones.
        
        :param list entities: The set of :class:`~sgsession.entity.Entity` to
            create structure for.
        :param str schema_name: Which schema to use. Defaults to ``'v1'``
        :param bool dry_run: Don't actually create structure. Defaults to ``False``.
        :param bool verbose: Print out what is going on. Defaults to ``False``.
        :return: ``dict`` mapping entities to paths.
        
        """
        structure = self.structure_from_entities(entities)
        return dict(structure.tag_existing(**kwargs))
    
    def find_template(self, entity, template_name):
        """Find a :class:`.BoundTemplate` within the :class:`.Structure` of the
        given :class:`~sgsession:sgsession.entity.Entity`.
        
        :param entity: The :class:`~sgsession:sgsession.entity.Entity` whose
            :class:`.Structure` should be searched for a template.
        :param str template_name: The name of the template to look for.
        :returns: :class:`.BoundTemplate` or ``None``.
        
        """
        structure = self.structure_from_entities([entity])
        for template in structure.iter_templates(template_name):
            return template
    
    def path_from_template(self_, entity_, template_name, *args, **kwargs):
        """Construct a path.
        
        :param entity: The :class:`~sgsession:sgsession.entity.Entity` whose
            :class:`.Structure` should be searched for a template.
        :param str template_name: The name of the template to look for.
        :param kwargs: Values to pass to :meth:`.BoundTemplate.format`.
        :returns str: The absolute path.
        :raises ValueError: When the template cannot be found.
        
        ::
        
            >>> sgfs.path_from_template(shot, 'maya_scene_publish',
            ...     version=123,
            ...     name='My_Publish',
            ...     ext=123,
            ... )
            '/Project/SEQ/AA/AA_001/maya/scenes/published/v0123/AA_001_My_Publish_v0123.mb'
            
        """
        template = self_.find_template(entity_, template_name)
        if not template:
            raise ValueError('could not find template %r under %r' % (template_name, entity_))
        return template.format(*args, **kwargs)
    
    def template_from_path(self, path, template_name):
        """Parse a path from a given template.
        
        :param str path: The absolute path to attempt to parse.
        :param str template_name: The name of the template to use to parse it.
        :returns: (:class:`.BoundTemplate`, :class:`.MatchResult`) tuple, or ``None``.
        
        """
        entities = self.entities_from_path(path)
        structure = self.structure_from_entities(entities)
        for template in structure.iter_templates(template_name):
            res = template.match(path)
            if res is not None:
                return template, res

    def parse_user_input(self, spec, entity_types=None, **kwargs):
        """Parse user input into an entity.

        :param str spec: The string of input from the user.
        :param tuple entity_types: Acceptable entity types. Effective against
            paths.
        :param kwargs: Passed to :meth:`~sgsession.session.Session.parse_user_input`.
        :return: :class:`.Entity` or ``None``.

        This is a wrapper around :meth:`~sgsession.session.Session.parse_user_input`
        which adds the ability to parse paths, looking for SGFS tags, e.g.::

            >>> sgfs.parse_user_input('/path/to/task123')
            <Entity Task:123 at 0x110863618>

        """

        # Paths (which must have been created via SGFS).
        path = os.path.abspath(spec)
        if os.path.exists(path):
            entities = self.entities_from_path(path, entity_type=entity_types)
            if entities:
                entity = entities[0]
                # This is a little gross, but what we have been doing so far.
                #print 'setting __path__ to', path
                entity.setdefault('__path__', path)
                return entity
        
        # Delegate to the underlying session.
        return self.session.parse_user_input(spec, entity_types, **kwargs)

