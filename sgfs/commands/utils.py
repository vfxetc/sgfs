
def parse_spec(sgfs, spec, entity_types=None, project_from_page=False):

    # TODO: Formally deprecate this.

    # We used to accept multiple parameters, but now we just take one.
    if not isinstance(spec, basestring):
        if not spec:
            spec = '.'
        elif len(spec) == 1:
            spec = spec[0]
        else:
            raise TypeError('spec must be string or single-item list', spec)
    
    return sgfs.parse_user_input(spec, entity_types=entity_types, fetch_project_from_page=project_from_page)
