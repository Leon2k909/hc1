import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
STAGE=Path(__file__).resolve().parent
BEFORE=STAGE.parent/'flood-lighting-before-20261020'
models=M.build(visual_chunks=['ground'])
m=models['ground']
triangles=M.K.write_model(STAGE/M.RES,M.RES,'ground',m)
lights=[M.scene_light(i,*row) for i,row in enumerate(M.LIGHTS)]
(STAGE/'lights.json').write_text(json.dumps(lights,indent=2)+'\n')
old=(BEFORE/'Assets/models/maps/forestbase/ground.vmdl').read_text()
new=(STAGE/M.RES/'ground.vmdl').read_text()
marker='_class = "PhysicsShapeList"'
assert marker in old and marker in new
assert old[old.index(marker):]==new[new.index(marker):], 'Ground collision changed'
layout=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
previous=layout['stats']['ground']
assert previous['triangles']==triangles
assert previous['boxes']==len(m.boxes) and previous['hulls']==len(m.hulls)
report=dict(ground=dict(triangles=triangles,boxes=len(m.boxes),hulls=len(m.hulls)),
            exactCollisionPreserved=True,lights=len(lights),floods=sum(r['Name'].startswith('Flood ') for r in lights),
            sourceSceneBeforeSha256=hashlib.sha256((BEFORE/'Assets/scenes/maps/forestbase/forestbase.scene').read_bytes()).hexdigest())
(STAGE/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
