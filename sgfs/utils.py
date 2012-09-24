def eval_expr_or_func(src, globals_, locals_=None):
    lines = src.strip().splitlines()
    if len(lines) > 1:
        # Surely I can create a function object directly with a compiled code
        # object, but I couldn't quit figure it out in the time that I allowed.
        # Ergo, we are evalling strings. Sorry.
        src = 'def _():\n' + '\n'.join('\t' + line for line in lines)
        locals_ = locals_ if locals_ is not None else {}
        code = compile(src, '<str>', 'exec')
        eval(code, globals_, locals_)
        try:
            return locals_['_']()
        except Exception, e:
            raise ValueError('Error while running %r -> %r' % (src, e))
    else:
        try:
            return eval(lines[0], globals_)
        except Exception, e:
            raise ValueError('Error while running %r -> %r' % (lines[0], e))
 