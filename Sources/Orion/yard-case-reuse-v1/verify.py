"""Independent exact scope, shared asset and camera-placement checks for the reuse preview."""
from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/yard-case-reuse-v1';plan=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in plan['protected'].items():assert sha(ROOT/p)==h,f'Protected file changed: {p}'
for p,h in plan['files'].items():assert sha(OUT/'stage/Assets'/p)==h and sha(ROOT/'Assets'/p)==h,p
source=(ROOT/'Assets/models/maps/orion/orion_props.obj').read_text().splitlines();folder=ROOT/'Assets/models/props/orion/yard_case_reuse_v1'
before=(folder/'before.obj').read_text().splitlines();preview=(folder/'preview.obj').read_text().splitlines()
for prefix in ('v ','vn ','vt '):assert [x for x in source if x.startswith(prefix)]==[x for x in preview if x.startswith(prefix)]
oldfaces=[l for l in before if l.startswith('f ')];assert len(oldfaces)==plan['original_triangles']==568
cut=set(plan['original_face_lines']);assert [l for i,l in enumerate(source) if l.startswith('f ') and i not in cut]==[l for l in preview if l.startswith('f ')]
def exact_faces(lines,selection=None):
    attrs=[[line.split()[1:] for line in lines if line.startswith(prefix)] for prefix in ('v ','vt ','vn ')]
    paint='';result=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f ') and (selection is None or i in selection):
            result.append((paint,[[attrs[k][int(n)-1] for k,n in enumerate(t.split('/'))] for t in line.split()[1:]]))
    return result
assert exact_faces(source,cut)==exact_faces(before),'Baseline changed original positions, UVs, normals or materials'
doc=(ROOT/'Assets/models/maps/orion/orion_props.vmdl').read_text();assert (folder/'preview.vmdl').read_text()==doc.replace('filename = "models/maps/orion/orion_props.obj"','filename = "models/props/orion/yard_case_reuse_v1/preview.obj"')
after=ROOT/'Assets/models/props/collider/equipment-case-trial-v1/after.obj';v=[];f=[]
for line in after.read_text().splitlines():
    if line.startswith('v '):v.append(line.split()[1:])
    elif line.startswith('f '):f.append([int(t.split('/')[0])-1 for t in line.split()[1:]])
v=np.array(v,float);f=np.array(f,int);assert np.isfinite(v).all() and len(f)==plan['replacement_triangles']
cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);assert (np.linalg.norm(cross,axis=1)>1e-8).all()
# OBJ (x,z,y) converts to engine (y,-x,z), then the existing model is scaled in engine axes.
world=v[:,[2,0,1]]*np.array((1,-1,1))*np.array(plan['scale_world'])+np.array(plan['position_world'])
lo,hi=world.min(0),world.max(0);assert abs(lo[2]-5.7)<.001 and hi[2]<53
for path in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',(folder/'preview.vmdl').read_text()):assert (ROOT/'Assets'/path).is_file(),path
native=json.loads((OUT/'native/validation.json').read_text());assert native['PreviewOnly'] and native['Triangles']==15568 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
compiled=json.loads((OUT/'compilation.json').read_text());assert len(compiled)==3 and all(row['Success'] for row in compiled)
assert native['PlayerFloorHit'] and abs(native['PlayerFloorZ'])<.5,native
report=dict(preview_only=True,shared_approved_case_reused=True,original_case_exactly_matched=568,only_selected_case_omitted_in_private_preview=True,
    original_pallet_retained=True,public_scene_and_props_unchanged=True,shared_model_and_materials_unchanged=True,no_added_collision=True,
    replacement_triangles=15568,world_bounds=[lo.tolist(),hi.tolist()],camera_at_player_height_on_yard_floor=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
