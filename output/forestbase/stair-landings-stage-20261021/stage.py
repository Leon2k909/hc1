import sys,json,collections,re
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
stage=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-stage-20261021")
models=F.build(visual_chunks=['barracks','command'])
report={}
def shape_blocks(text):
    return re.findall(r'\{\n\s*_class = "PhysicsShapeBox"[\s\S]*?\n\s*\},',text)
for name in ('barracks','command'):
    K.write_obj(stage/(name+'.obj'),models[name],name)
    K.write_vmdl(stage/(name+'.vmdl'),F.RES,name,models[name])
    old=(root/'Assets/models/maps/forestbase'/(name+'.vmdl')).read_text()
    new=(stage/(name+'.vmdl')).read_text()
    assert old.split('_class = "PhysicsShapeList"')[0]==new.split('_class = "PhysicsShapeList"')[0],(name,'Changed render/material import metadata')
    before=collections.Counter(shape_blocks(old));after=collections.Counter(shape_blocks(new))
    removed=before-after;added=after-before
    assert sum(removed.values())<=33,(name,'Too many removed shapes')
    assert not models[name].hulls
    assert (root/'Assets/models/maps/forestbase'/(name+'.mtl')).read_bytes()==(stage/(name+'.mtl')).read_bytes()
    report[name]={'boxesBefore':sum(before.values()),'boxesAfter':sum(after.values()),'unchangedBoxes':sum((before&after).values()),'removedBoxes':sum(removed.values()),'addedBoxes':sum(added.values()),'hulls':len(models[name].hulls)}
    (stage/(name+'-physics-delta.json')).write_text(json.dumps({'removed':list(removed.elements()),'added':list(added.elements())},indent=2))
# Record the new stair endpoints without regenerating the live scene or scenery.
layout=json.loads((root/'output/forestbase/layout.json').read_text())
layout['routes']=F.ROUTES
(stage/'layout.json').write_text(json.dumps(layout,indent=2))
(stage/'geometry-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
