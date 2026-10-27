import sys,json,shutil,collections
from pathlib import Path
root=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import forestbase_forklift as T
import map_kit as K
out=Path(__file__).parent
T.materials(out/'materials');print('Forklift PBR materials staged',flush=True)
m=F.build(visual_chunks=['logistics'])['logistics']
count=K.write_obj(out/'logistics.obj',m,'logistics');K.write_vmdl(out/'logistics.vmdl',F.RES,'logistics',m)
old=(out/'logistics-before.vmdl').read_text();new=(out/'logistics.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):],'Unexpected physics change'
for p in out.glob('logistics_hulls_*.obj'):assert p.read_bytes()==(root/'Assets/models/maps/forestbase'/p.name).read_bytes()
# Count all transit case triangles: the earlier crate replacement is preserved.
def groups(path):
    result=collections.Counter();group=None
    for s in path.open():
        if s.startswith('usemtl '):group=s.split()[1]
        elif s.startswith('f '):result[group]+=1
    return result
before=groups(out/'logistics-before.obj');after=groups(out/'logistics.obj')
for p in ('transit_front','transit_shell','transit_hardware'):assert before[p]==after[p]
audit=dict(triangles=count,trianglesBefore=sum(before.values()),collisionUnchanged=True,transitCasesPreserved=True,
           materialSlots=len(m.polygons),boxes=len(m.boxes),hulls=len(m.hulls),location=[1130,-860,0],yaw=-25)
(out/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
