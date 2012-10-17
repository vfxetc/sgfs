
@graph
def main():
    fix = LargeFixture()
    tasks = fix.session.merge(fix.tasks)
    ctx = fix.sgfs.context_from_entities(tasks)
    return ctx.dot()

@graph
def linear():
    fix = LargeFixture()
    tasks = fix.session.merge(fix.tasks)
    ctx = fix.sgfs.context_from_entities(tasks)
    for x in ctx.iter_linearized():
        yield x.dot()