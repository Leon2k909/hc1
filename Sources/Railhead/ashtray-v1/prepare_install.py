"""Replace every live old ash column; preserve both dressing models and physics."""
from pathlib import Path
import hashlib,json,re,sys,collections
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/ashtray-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
before=OUT/'install-before';stage=OUT/'install-stage';dest=stage/'Assets/models/maps/railhead/ashtray-v1';dest.mkdir(parents=True,exist_ok=True)
def backup(p):
 b=before/p.relative_to(ROOT);b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(p.read_bytes())
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();X,Y,Z='):build.index(';count=K.write_model')]
helper='''"""Approved stainless smoking-area columns, exact prototype geometry and UVs."""
import math
import numpy as np
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
def model(e=601.,n=-891.,z0=0.,r=4.,height=40.):
    target_origin=np.array((e,n,z0))
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''
    offset=K.uv_offset('ashtray')
    for paint,faces in m.polygons.items():
        for i,(points,normal) in enumerate(faces):
            if (paint,i) not in m.polygon_uvs:
                world=[K.to_world(p) for p in points];wn=K.to_world(normal);tile=m.tile_overrides[paint]
                m.polygon_uvs[(paint,i)]=[K.face_uv(p,wn,paint,offset,tile) for p in world]
    scale=np.array((r/4.,r/4.,height/40.));delta=target_origin
    for paint,faces in m.polygons.items():
        moved=[]
        for i,(points,normal) in enumerate(faces):
            nn=normal/scale;nn=nn/np.linalg.norm(nn)
            smooth=m.polygon_normals.get((paint,i))
            if smooth is not None:
                m.polygon_normals[(paint,i)]=[K.normalise(q/scale) for q in smooth]
            moved.append(([(p-O)*scale+delta for p in points],nn))
        m.polygons[paint]=moved
    return m

def append_to(target,e,n,z0=0.,r=4.,height=40.):
    target.collision_box((e-r,n-r,z0),(e+r,n+r,z0+height),D.METAL)
    m=model(e,n,z0,r,height)
    for paint,faces in m.polygons.items():
        alias='rh_as_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))
'''
helper_path=ROOT/'Tools/railhead_ashtray.py';helper_path.write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import railhead_ashtray as F;import railhead_dress_detail as D;import railhead_map as R
candidate=ROOT/'Assets/models/maps/railhead/ashtray-v1/ashtray.obj';proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'ashtray')
assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:],'Generator geometry/UV mismatch'
positions={};inputs={};removed_counts={}
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';faces=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):faces.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,faces
own=candidate.with_suffix('.vmdl').read_text();pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},';node=re.search(pattern,own,re.S).group()
remaps=[r.replace('from = "','from = "rh_as_') for r in re.findall(r'\{ from = "[^\n]+?\}',own)]
for side,sign in (('east',1),('west',-1)):
 public=ROOT/f'Assets/models/maps/railhead/railhead_dress_{side}.vmdl';original=public.read_text();assert 'installed_ashtrays' not in original,'Already installed'
 source_rel=re.search(r'filename = "([^"]+\.obj)"',original)[1];source=ROOT/'Assets'/source_rel
 for p in (public,source):backup(p);inputs[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
 positions[side]=[(sign*e,-891.,0.) for e in (601.,1131.)]
 legacy=K.Model();new=K.Model()
 for e,n,z0 in positions[side]:D.ashtray_pillar(legacy,e,n,z0);F.append_to(new,e,n,z0)
 new.boxes=[];new.hulls=[];R.configure(legacy);oldobj=OUT/f'legacy-{side}.obj';K.write_obj(oldobj,legacy,'legacy_ashtray')
 _,old=records(oldobj);wanted=collections.Counter(key for _,key in old);lines,faces=records(source);removed=set()
 for i,key in faces:
  if wanted[key]:removed.add(i);wanted[key]-=1
 assert not +wanted,(side,+wanted);assert len(removed)==588
 target=stage/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(''.join(l for i,l in enumerate(lines) if i not in removed))
 removed_counts[side]=len(removed);obj=dest/f'installed_ashtrays_{side}.obj';K.write_obj(obj,new,'ashtray')
 add=node.replace('ashtray.obj',obj.name);oldnode=re.search(pattern,original,re.S).group();merged=original.replace(oldnode,oldnode+'\n'+add,1)
 assert not set(re.findall(r'from = "([^"]+)"','\n'.join(remaps)))&set(re.findall(r'from = "([^"]+)"',original))
 index=merged.index('\t'*7+'{ from = ');merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
 marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
 target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
generator=ROOT/'Tools/railhead_dress_detail.py';backup(generator);g=generator.read_text();a=g.index('def ashtray_pillar(');b=g.index('\ndef wall_sign(',a)
(HERE/'legacy_function.py.txt').write_text(g[a:b]);g=g[:a]+'''def ashtray_pillar(model,e,n,z0=0.0,r=4.0,height=40.0):
    """Approved formed stainless column, preserving the original thin collider."""
    from railhead_ashtray import append_to
    append_to(model,e,n,z0,r,height)

'''+g[b:];generator.write_text(g)
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before=inputs,files=files,positions=positions,old_triangles=removed_counts,new_triangles=39648),indent=2))
script=(ROOT/'Sources/Railhead/brick-pallet-v1/install.cs.txt').read_text().replace('brick-pallet-v1','ashtray-v1').replace('InstalledPallets=1','InstalledAshtrays=4');(HERE/'install.cs.txt').write_text(script)
print(json.dumps(dict(columns=4,old_triangles_removed=1176,new_triangles=39648,generator_matches_approved=True,files=len(files))))
