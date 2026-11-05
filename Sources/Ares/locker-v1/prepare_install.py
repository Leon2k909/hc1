"""Replace both banks with the approved locker, preserving all shared hall data."""
from pathlib import Path
import sys,re,json,hashlib,collections,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/ares/locker-v1'
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import ares_map as R
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
stage=OUT/'install-stage';before=OUT/'install-before';stage.mkdir(exist_ok=True);before.mkdir(exist_ok=True)
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();X='):build.index('R.configure(m);count=')]
body=body.replace('C=np.array((1278.,-709.,0.))','C=np.array((float(e),float(n),float(z0)))')
body=body.replace("segments={'0':'abcedf','4':'bcfg'}", "segments={'0':'abcedf','1':'bc','2':'abged','3':'abgcd','4':'bcfg','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abcdfg'}")
body=body.replace("enumerate('04')", "enumerate(f'{int(number):02d}')")
helper='''"""Approved Ares lockers; original steel/brass and lighter formed doors."""
import math
import numpy as np
import map_kit as K
import ares_materials as AM
import riverdale_parts as G
import railhead_dress_detail as D
def model(e,number,n=-709.,z0=0.):
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    for paint in m.polygons:
        m.material_overrides[paint]=f"{AM.RESOURCE_DIR}/{paint}.vmat"
        m.tile_overrides[paint]=AM.TILES.get(paint,64.)
    return m

def append_to(target,e,number,n=-709.,z0=0.):
    m=model(e,number,n,z0)
    for paint,faces in m.polygons.items():
        alias="ar_in_locker_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            uv=m.polygon_uvs.get((paint,i))
            if uv is None:
                uv=[K.face_uv(K.to_world(p),K.to_world(normal),paint,K.uv_offset('locker'),m.tile_overrides[paint]) for p in points]
            target.polygon(alias,points,normal,uv=uv,normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/ares_lockers.py').write_text(helper)
import ares_lockers as N
proof=OUT/'approved-generator.obj';K.write_obj(proof,N.model(1278.,4),'locker')
candidate=ROOT/'Assets/models/maps/ares/locker-v1/locker.obj'
assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
old=K.Model();new=K.Model();positions=[]
for s in (1,-1):
 for k in range(7):
  e=s*(1200.+26*k);number=k+1 if s>0 else k+8
  old.box((e-12.5,-720,0),(e+12.5,-698,84),{'default':'ar_steel','+n':'ar_gunmetal'})
  old.box((e-2,-698,50),(e+2,-697,56),'ar_brass')
  N.append_to(new,e,number);positions.append(dict(e=e,n=-709,z=0,number=number))
new.uv_source_name='locker'
dest=stage/'Assets/models/maps/ares/locker-v1';dest.mkdir(parents=True,exist_ok=True)
triangles=K.write_obj(dest/'installed_lockers.obj',new,'installed_lockers')
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
R.configure(old);K.write_obj(OUT/'legacy-all-lockers.obj',old,'legacy_all_lockers');_,faces=records(OUT/'legacy-all-lockers.obj');wanted=collections.Counter(key for _,key in faces)
source=ROOT/'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj';lines,faces=records(source);removed=set()
for i,key in faces:
 if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted and len(removed)==336
def backup(path):
 rel=path.relative_to(ROOT);target=before/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);return rel
rel=backup(source);(stage/rel).parent.mkdir(parents=True,exist_ok=True);(stage/rel).write_text(''.join(l for i,l in enumerate(lines) if i not in removed))
public=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';rel=backup(public);original=public.read_text();assert 'locker-v1/installed_lockers.obj' not in original
own=candidate.with_suffix('.vmdl').read_text();node=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',own,re.S).group()
node=node.replace('locker.obj','installed_lockers.obj').replace('name = "locker"','name = "storage_lockers"')
first=re.search(r'\{\s*_class = "RenderMeshFile"',original);merged=original[:first.start()]+node+'\n'+original[first.start():]
remaps=[f'{{ from = "{paint}.vmat" to = "{path}" }},' for paint,path in new.material_overrides.items()]
for paint in new.material_overrides:assert f'from = "{paint}.vmat"' not in original
index=merged.index('remaps =');index=merged.index('[',index)+1;merged=merged[:index]+'\n'+'\n'.join(remaps)+merged[index:]
marker='_class = "PhysicsShapeList"';assert merged[merged.index(marker):]==original[original.index(marker):]
(stage/rel).write_text(merged)
before_hashes={str(p.relative_to(before)).replace('\\','/'):sha(p) for p in before.rglob('*') if p.is_file()}
generator=ROOT/'Tools/ares_map.py';backup(generator);g=generator.read_text()
oldblock='''    # Lockers along the south wall's east (west) part.
    for k in range( 7 ):
        e = s * ( 1200.0 + k * 26.0 )
        lo = ( e - 12.5, HALL_N0, 0 )
        hi = ( e + 12.5, HALL_N0 + 22, 84 )
        m.box( lo, hi, { "default": "ar_steel", "+n": "ar_gunmetal" } )
        m.box( ( e - 2, HALL_N0 + 22, 50 ), ( e + 2, HALL_N0 + 23, 56 ), "ar_brass" )'''
assert g.count(oldblock)==1;(HERE/'legacy_function.py.txt').write_text(oldblock)
replacement='''    # The approved lockers retain the bank's original cover collider below.
    from ares_lockers import append_to as append_approved_locker
    for k in range( 7 ):
        e = s * ( 1200.0 + k * 26.0 )
        append_approved_locker( m, e, k + 1 if s > 0 else k + 8, HALL_N0 + 11 )'''
generator.write_text(g.replace(oldblock,replacement))
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before=before_hashes,files=files,lockers=14,removed_triangles=336,new_triangles=triangles,positions=positions,generator_matches_approved=True),indent=2))
print(json.dumps(dict(lockers=14,old_triangles_removed=336,new_triangles=triangles,files=len(files),generator_matches_approved=True)))
