"""Replace all ten shared picnic tables, including canonical regeneration caches."""
from pathlib import Path
import sys,re,json,hashlib,collections,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/belltower/picnic-table-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as R
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());assert all(sha(ROOT/p)==h for p,h in guard.items()),'Guarded source changed'
stage=OUT/'install-stage';before=OUT/'install-before';stage.mkdir(exist_ok=True);before.mkdir(exist_ok=True)
centres=((-1130.,-620.),(-1030.,-620.),(-800.,-600.),(-800.,-780.),(-1110.,-830.))
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();p='):build.index('count=K.write_model')]
body=body.replace('m=K.Model();p=R.Place((-800.,-600.,0.),90.);X,Y,Z=p.x,p.y,p.z','m=K.Model();X,Y,Z=p.x,p.y,p.z')
helper='''"""Approved Belltower picnic table, shared by both beer gardens."""
import numpy as np
import map_kit as K
import belltower_furniture as F
import railhead_dress_detail as D
def model(p):
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    return m

def append_to(target,p):
    m=model(p)
    for paint,faces in m.polygons.items():
        alias="bt_pt_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
helper_path=ROOT/'Tools/belltower_picnic_table.py';helper_path.write_text(helper)
import belltower_picnic_table as N
proof=OUT/'approved-generator.obj';K.write_obj(proof,N.model(R.Place((-800.,-600.,0.),90.)),'picnic_table')
candidate=ROOT/'Assets/models/maps/belltower/picnic-table-v1/picnic_table.obj'
assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
new_west=K.Model();old_west=K.Model()
for centre in centres:
 N.append_to(new_west,R.Place((*centre,0.),90.));R.picnic_table(old_west,centre,90.)
new_east=new_west.mirrored(R.EAST_PAINTS);old_east=old_west.mirrored(R.EAST_PAINTS)
resource='models/maps/belltower/picnic-table-v1';asset_dir=stage/'Assets'/resource;asset_dir.mkdir(parents=True,exist_ok=True)
for side,m in (('west',new_west),('east',new_east)):K.write_obj(asset_dir/f'installed_{side}.obj',m,f'installed_{side}')
def signature(points,paint):return paint,tuple(sorted(tuple(round(float(q),3) for q in p) for p in points))
def legacy_signatures(m):
 return collections.Counter(signature([(-p[0],p[2],p[1]) for p in points],paint) for paint,faces in m.polygons.items() for points,_ in faces for _unused in [None] for points in [[points[0],points[k],points[k+1]] for k in range(1,len(points)-1)])
def backup(path):
 rel=path.relative_to(ROOT);dest=before/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copyfile(path,dest)
 return rel
originals={};splices=[]
def splice(source,wanted,append=None):
 """Stream the large cache, retaining every byte except matched face lines."""
 rel=backup(source);originals[str(rel).replace('\\','/')]=sha(source)
 dest=stage/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 interesting={};nv=nt=nn=removed=0;paint=''
 sign=-1 if '/west/' in str(source).replace('\\','/') or source.stem.endswith('_west') else 1
 # OBJ x=-e; choose both gardens' coordinate bands without retaining the whole town.
 with source.open(encoding='utf-8',newline='') as inp,dest.open('w',encoding='utf-8',newline='') as out:
  for line in inp:
   if line.startswith('v '):
    nv+=1;q=tuple(map(float,line.split()[1:4]))
    if .0-1e-3<=q[1]<=30.001 and 740<=abs(q[0])<=1190 and -875<=q[2]<=-550:interesting[nv]=tuple(round(v,3) for v in q)
   elif line.startswith('vt '):nt+=1
   elif line.startswith('vn '):nn+=1
   elif line.startswith('usemtl '):paint=line.split()[1]
   elif line.startswith('f ') and paint in ('planks','planks_dark'):
    ids=[int(v.split('/')[0]) for v in line.split()[1:]]
    if all(i in interesting for i in ids):
     key=(paint,tuple(sorted(interesting[i] for i in ids)))
     if wanted[key]:wanted[key]-=1;removed+=1;continue
   out.write(line)
  if append:
   out.write('\n# Approved picnic tables; old render faces removed\n')
   for line in append.read_text().splitlines():
    if line.startswith(('mtllib ','# ')):continue
    if line.startswith('f '):
     values=[]
     for value in line.split()[1:]:
      a,b,c=map(int,value.split('/'));values.append(f'{a+nv}/{b+nt}/{c+nn}')
     line='f '+' '.join(values)
    out.write(line+'\n')
 splices.append(dict(path=str(rel).replace('\\','/'),removed=removed,appended=append is not None))
 return removed
for side,new,old in (('west',new_west,old_west),('east',new_east,old_east)):
 public=ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl';rel=backup(public);originals[str(rel).replace('\\','/')]=sha(public)
 original=public.read_text();assert 'picnic-table-v1/installed_' not in original,'Already installed'
 paths=re.findall(r'filename = "([^"]+\.obj)"',original)
 wanted=legacy_signatures(old)
 for path in paths:
  if re.search(fr'{side}_\d+_planks(?:_dark)?\.obj$',path):splice(ROOT/'Assets'/path,wanted)
 assert not +wanted,(side,'Bounded imports did not contain exactly five old tables')
 canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
 wanted=legacy_signatures(old);assert splice(canonical,wanted,asset_dir/f'installed_{side}.obj')==300
 assert not +wanted
 canonical_mtl=canonical.with_suffix('.mtl');mtlrel=backup(canonical_mtl);originals[str(mtlrel).replace('\\','/')]=sha(canonical_mtl)
 (stage/mtlrel).write_text(canonical_mtl.read_text()+'\n'+(asset_dir/f'installed_{side}.mtl').read_text())
 # Add the replacement render import while preserving every existing node.
 own=(candidate.with_suffix('.vmdl')).read_text();node=re.search(r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},',own,re.S).group()
 node=node.replace('picnic_table.obj',f'installed_{side}.obj').replace('name = "picnic_table"',f'name = "picnic_tables_{side}"')
 first=re.search(r'\{\s*_class = "RenderMeshFile"',original);assert first
 merged=original[:first.start()]+node+'\n'+original[first.start():]
 remaps=[f'{{ from = "{alias}.vmat" to = "{path}" }},' for alias,path in new.material_overrides.items()]
 for alias in new.material_overrides:assert f'from = "{alias}.vmat"' not in original
 index=merged.index('remaps =');index=merged.index('[',index)+1;merged=merged[:index]+'\n'+'\n'.join(remaps)+merged[index:]
 marker='_class = "PhysicsShapeList"';assert merged[merged.index(marker):]==original[original.index(marker):]
 (stage/rel).write_text(merged)
generator=ROOT/'Tools/belltower_map.py';backup(generator)
g=generator.read_text();start=g.index('def picnic_table( model, centre, yaw, z=0.0 ):');end=g.index('\n\n# ',start)
legacy_function=g[start:end];(HERE/'legacy_function.py.txt').write_text(legacy_function)
replacement='''def picnic_table( model, centre, yaw, z=0.0 ):
    p = Place( ( centre[0], centre[1], z ), yaw )
    from belltower_picnic_table import append_to
    append_to( model, p )
    p.box( model, ( -42, -36, 0 ), ( 42, 36, 30 ), None, WOOD )
'''
generator.write_text(g[:start]+replacement+g[end:])
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before=originals,files=files,splices=splices,tables=10,removed_live_triangles=600,generator_matches_approved=True),indent=2))
print(json.dumps(dict(tables=10,old_live_triangles_removed=600,files=len(files),splices=splices,generator_matches_approved=True)))
