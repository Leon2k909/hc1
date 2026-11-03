"""Replace the sliding leaf's render mesh with Ares's existing formed-pressure-door design.

Keeps the active model path, GUID, scene, automatic controller and the complete
ModelDoc physics section. Run once on the original simple sliding leaf.
"""
from pathlib import Path
import hashlib,json,re,shutil,sys
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as P
import ares_pressure_formed as F
OUT=ROOT/'output/ares/sliding-pressure-leaf-20261031';OUT.mkdir(parents=True,exist_ok=True)
target=ROOT/'Assets/models/maps/ares/sliding-doors-v1/ares_sliding_leaf.obj'
doc=target.with_suffix('.vmdl');mtl=target.with_suffix('.mtl');scene=ROOT/'Assets/scenes/maps/Ares/ares.scene'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
initial={p:sha(p) for p in (target,doc,mtl,scene,ROOT/'Code/World/AutomaticSlidingDoor.cs',ROOT/'Tools/ares_pressure_formed.py')}
vmdl=doc.read_bytes().decode();oldmtl=mtl.read_bytes().decode()
assert 'ar_pd_body.vmat' not in vmdl,'Already upgraded or modified'
text=(ROOT/'Tools/ares_pressure_formed.py').read_text()
start=text.index('    for side in (-1,1):\n        leaf=leaf_profile',text.index('def pressure_door('))
end=text.index('    # An overlapping central weather/pressure strip',start)
loop=text[start:end].replace("facepaint='cassette'","facepaint='panel'")
# A single leaf is mirrored by the existing right-hand scene object. Reuse the
# actual formed panel, recessed grips, worn bevels, kick plate and wheel.
body=loop.split('\n',1)[1];body='\n'.join(line[4:] if line.startswith('    ') else line for line in body.split('\n'))
scope=vars(F).copy();exec('def one_leaf(m, width, height, unit, side):\n'+body+'\n',scope)
original=K.Model();scope['one_leaf'](original,224.,176.,1,-1);F.wheel(original,-38.,58.,9.)
pts=np.vstack([p for polys in original.polygons.values() for p,n in polys]);lo=pts.min(axis=0);hi=pts.max(axis=0)
assert np.isfinite(pts).all() and hi[0]<0 and hi[1]<0
sx=111.8/(hi[0]-lo[0]);sy=3.75/(hi[1]-lo[1]);sz=171.5/(hi[2]-lo[2]);mid_x=(lo[0]+hi[0])/2;mid_z=(lo[2]+hi[2])/2
new=K.Model()
for paint,polys in original.polygons.items():
    for i,(points,normal) in enumerate(polys):
        for sign in (-1,1):
            transformed=[((p[0]-mid_x)*sx,(p[1]-hi[1])*sy*sign,(p[2]-mid_z)*sz) for p in points]
            def direction(n):
                v=np.array((n[0]/sx,n[1]/(sy*sign),n[2]/sz));return v/np.linalg.norm(v)
            normals=original.polygon_normals.get((paint,i));uv=original.polygon_uvs.get((paint,i))
            P.card(new,paint,transformed,direction(normal),uv=uv,normals=[direction(n) for n in normals] if normals is not None else None)
new.material_overrides.update(F.MATERIALS);new.tile_overrides.update({k:24. for k in F.MATERIALS})
assert not new.boxes and not new.hulls
allpoints=np.vstack([p for polys in new.polygons.values() for p,n in polys]);bounds=[allpoints.min(axis=0),allpoints.max(axis=0)]
assert np.all(bounds[0]>=np.array((-56,-4,-86))-.001) and np.all(bounds[1]<=np.array((56,4,86))+.001),bounds
stage=OUT/'stage';stage.mkdir(exist_ok=True);staged_obj=stage/'ares_sliding_leaf.obj'
triangles=K.write_obj(staged_obj,new,'ares_sliding_leaf');assert triangles>10000
# The exporter rounds vertices to three decimals; discard any triangles that
# collapse at that precision without changing the remaining geometry or UVs.
vertices=[];retained=[];degenerate=0
for line in staged_obj.read_text().splitlines(keepends=True):
    p=line.split()
    if p and p[0]=='v':vertices.append(np.array(list(map(float,p[1:]))))
    elif p and p[0]=='f':
        pts=[vertices[int(x.split('/')[0])-1] for x in p[1:]]
        if np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))<=1e-8:degenerate+=1;continue
    retained.append(line)
staged_obj.write_text(''.join(retained));triangles-=degenerate
used=set(new.polygons);assert used and used<=set(F.MATERIALS)
for material in used:assert (ROOT/'Assets'/F.MATERIALS[material]).exists(),material
remap_end=vmdl.index(']',vmdl.index('remaps ='))
added=''.join(f'{{ from = "{p}.vmat" to = "{F.MATERIALS[p]}" }},\n' for p in sorted(used))
newdoc=vmdl[:remap_end]+',\n'+added.rstrip(',\n')+'\n'+vmdl[remap_end:]
# The unchanged physics is reused by the existing moving ModelCollider.
assert newdoc[newdoc.index('_class = "PhysicsShapeList"'):]==vmdl[vmdl.index('_class = "PhysicsShapeList"'):]
newmtl=oldmtl+'\n'+''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in sorted(used))
assert all(sha(path)==h for path,h in initial.items())
payloads=[(doc,newdoc.encode()),(mtl,newmtl.encode()),(target,staged_obj.read_bytes())];completed=[]
try:
    for path,_ in payloads:
        backup=OUT/'before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();shutil.copy2(path,backup)
    # Existing materials still compile while new remaps and MTL entries arrive;
    # atomically replace the OBJ only after its material names are available.
    for path,data in payloads:
        incoming=path.with_name(path.name+'.pressure-upgrade');incoming.write_bytes(data);incoming.replace(path);completed.append(path)
except BaseException:
    for path in reversed(completed):shutil.copy2(OUT/'before'/path.relative_to(ROOT),path)
    raise
assert sha(scene)==initial[scene]
report={'sourceDesign':'Ares formed pressure doors v3','panelsUpdated':4,'trianglesPerLeaf':triangles,'materials':sorted(used),
 'localBounds':[v.tolist() for v in bounds],'existingSceneAndAutomaticControllerUnchanged':True,'physicsDefinitionUnchanged':True,
 'beforeSHA256':{str(p.relative_to(ROOT)):h for p,h in initial.items()},'afterSHA256':{str(p.relative_to(ROOT)):sha(p) for p,_ in payloads},
 'nativePlaytestPerformed':False}
(OUT/'installation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
