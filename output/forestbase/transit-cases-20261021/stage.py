import sys,json,collections,hashlib,shutil
from pathlib import Path
root=Path('C:/Users/mimi-/Documents/S&box Projects/hc1')
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import forestbase_cases as C
import map_kit as K
out=Path(__file__).parent;before=out.parent/'transit-cases-before-20261021'
material=out/'materials'
if '--geometry' not in sys.argv:C.generate_materials(material)
print('Three case PBR atlases generated',flush=True)
chunks=['barracks','command','motor','workshop','yard','logistics']
models=F.build(visual_chunks=chunks)
report={}
for name in chunks:
    m=models[name]
    if not any(p.startswith('transit_') for p in m.polygons):continue
    original=root/'Assets/models/maps/forestbase'
    for ext in ('.obj','.vmdl','.mtl'):
        if not (before/(name+ext)).exists():shutil.copy2(original/(name+ext),before/(name+ext))
    count=K.write_obj(out/(name+'.obj'),m,name)
    K.write_vmdl(out/(name+'.vmdl'),F.RES,name,m)
    old=(original/(name+'.vmdl')).read_text();new=(out/(name+'.vmdl')).read_text()
    marker='_class = "PhysicsShapeList"'
    assert old[old.index(marker):]==new[new.index(marker):],name+' physics changed'
    for p in out.glob(name+'_hulls_*.obj'):
        assert p.read_bytes()==(original/p.name).read_bytes(),p.name
    report[name]={'triangles':count,'collisionUnchanged':True,'materialSlots':len(m.polygons),
                  'oldTriangles':sum(1 for line in (before/(name+'.obj')).open() if line.startswith('f '))}
    print(name,report[name],flush=True)
# Uninstalled unit model for an honest close inspection at actual map dimensions.
preview=F.model();C.case(preview,0,0,0,66,54,'olive',vars(F),variant=0)
K.write_obj(out/'case_preview.obj',preview,'case_preview')
K.write_vmdl(out/'case_preview.vmdl','models/maps/forestbase/transit_preview','case_preview',preview)
(out/'audit.json').write_text(json.dumps(report,indent=2))
print('STAGE COMPLETE',flush=True)
