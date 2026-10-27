import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'Tools'))
from forestbase_cascade_width_audit import groups
root=Path.cwd();before=root/'output/forestbase/rooftops-before-20261020';stage=root/'output/forestbase/rooftops-stage-20261020';res=Path('models/maps/forestbase')
report={}
allowed={'roof','roof_deck','rubber','structural_steel','case_hardware','steel','equipment_paint'}
for name in ('barracks','command'):
 a=groups(before/'Assets'/res/(name+'.obj'));b=groups(stage/res/(name+'.obj'))
 unchanged={p:a[p]==b[p] for p in a if p not in allowed};assert all(unchanged.values()),unchanged
 old=(before/'Assets'/res/(name+'.vmdl')).read_text();new=(stage/res/(name+'.vmdl')).read_text()
 token='_class = "PhysicsShapeList"';assert old.split(token,1)[1]==new.split(token,1)[1],name+' collision changed'
 assert 'roof' in a and 'roof_deck' in b
 report[name]={'unchangedInteriorFacadeProps':unchanged,'serializedCollisionIdentical':True,'roofMaterialReplaced':True,'oldMaterials':len(a),'newMaterials':len(b)}
scene=Path('Assets/scenes/maps/forestbase/forestbase.scene');assert (root/scene).read_bytes()==(before/scene).read_bytes()
report['sceneUnchanged']=True;report['scope']='Source geometry/material grouping and exact serialized collision. Native visuals and imports pending.'
(stage/'source-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
