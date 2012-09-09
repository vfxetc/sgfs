def eval_expr_or_func(src, globals_, locals_=None):
    lines = src.strip().splitlines()
    if len(lines) > 1:
        src = 'def _():\n' + '\n'.join('\t' + line for line in lines)
        locals_ = locals_ if locals_ is not None else {}
        code = compile(src, '<str>', 'exec')
        eval(code, globals_, locals_)
        return locals_['_']()
    else:
        return eval(lines[0], globals_)
 