@graph
def context_from_path():
    
    sg = Shotgun()
    sgfs = SGFS(root=sandbox, shotgun=sg)
    
    fix = Fixture(sg)
    proj = fix.Project('Example Project')
    seq = proj.Sequence("AA")
    shot = seq.Shot('AA_001')
    task = shot.Task('Do Work', id=123)
    task2 = shot.Task('Do More Work', id=234)
    
    ctx = sgfs.context_from_entities([task])
    yield ctx.dot()
    
    ctx = sgfs.context_from_entities([task, task2])
    yield ctx.dot()
