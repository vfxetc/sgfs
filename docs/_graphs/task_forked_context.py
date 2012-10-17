
@graph
def main():
    fix = LargeFixture()
    tasks = fix.session.merge(fix.tasks)
    ctx = fix.sgfs.context_from_entities(tasks)
    return ctx.dot()