import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
import forestbase_cascade as C
STAGE=Path(__file__).resolve().parent
BEFORE=STAGE.parent/'impact-mist-before-20261020'
material_output=STAGE/'materials/forestbase'
material_output.mkdir(parents=True,exist_ok=True)
original_cascade=C.build
C.build=lambda m:original_cascade(m,material_output=material_output)
reuse='--reuse-model' in sys.argv
models=M.build(visual_chunks=[] if reuse else ['vista'])
m=models['vista']
triangles=sum(len(line.split())-3 for line in (STAGE/M.RES/'vista.obj').read_text().splitlines() if line.startswith('f ')) if reuse else M.K.write_model(STAGE/M.RES,M.RES,'vista',m)
old=(BEFORE/'Assets/models/maps/forestbase/vista.vmdl').read_text()
new=(STAGE/M.RES/'vista.vmdl').read_text()
marker='_class = "PhysicsShapeList"'
assert (marker in old)==(marker in new)
if marker in old:
    assert old[old.index(marker):]==new[new.index(marker):], 'Vista collision changed'
else:
    assert not m.boxes and not m.hulls
previous=json.loads((BEFORE/'output/forestbase/layout.json').read_text())['stats']['vista']
assert previous['boxes']==len(m.boxes) and previous['hulls']==len(m.hulls)
grass=[dict(name=name,model=path,world=M.K.to_world(pos).tolist(),scale=scale,yaw=yaw)
       for name,path,pos,yaw,scale in M.INSTANCES if name.startswith('Shore grass ')]
assert len(grass)==24
(STAGE/'shore-grass.json').write_text(json.dumps(grass,indent=2)+'\n')
(STAGE/'scenery-instances.json').write_text(json.dumps([dict(name=name,model=path,world=M.K.to_world(pos).tolist(),scale=scale,yaw=yaw) for name,path,pos,yaw,scale in M.INSTANCES],indent=2)+'\n')
report=dict(vista=dict(triangles=triangles,boxes=len(m.boxes),hulls=len(m.hulls)),previousVista=previous,exactCollisionPreserved=True,shoreGrass=len(grass),
            materialSlots=sorted({line.split()[1] for line in (STAGE/M.RES/'vista.obj').read_text().splitlines() if line.startswith('usemtl ')}),scope='Rebuilt visual shoreline, stone grounding and matching grass heights; no collision or topology increase.')
(STAGE/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
