@graph
def context_from_entities():
    
    sg = Shotgun()
    fix = Fixture(sg)
    proj = fix.Project('Example Project')
    seq = proj.Sequence("AA")
    shot = seq.Shot('AA_001')
    task = shot.Task('Do Work', id=1234)
    sgfs = SGFS(root=sandbox, shotgun=sg)
    ctx = sgfs.context_from_entities([task])
    return ctx.dot()