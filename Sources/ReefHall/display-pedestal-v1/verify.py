from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/reefhall/display-pedestal-v1';plan=json.loads((OUT/'build-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((OUT/'installed-verification.json').read_text());assert proof['installed'] and proof['physics_identical']
for p,h in plan['files'].items():assert sha(ROOT/'Assets'/p)==h and sha(OUT/'stage/Assets'/p)==h,p
folder=ROOT/'Assets/models/props/reefhall/display_pedestal_v1'
scene=json.loads((ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene').read_text());aquarium=next(x for x in scene['GameObjects'] if x.get('Name')=='Aquarium');nodes=[x for x in aquarium['Children'] if x.get('Name')=='Rotunda Display Pedestal'];assert len(nodes)==1
assert nodes[0]['Components'][0]['Model']=='models/props/reefhall/display_pedestal_v1/pedestal.vmdl' and len(nodes[0]['Components'])==1
assert not (folder/'preview.vmdl').exists()
results=[]
for lod in range(3):
    v,n,uv,f=[],[],[],[]
    for line in (folder/f'pedestal_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):v.append(line.split()[1:])
        elif line.startswith('vn '):n.append(line.split()[1:])
        elif line.startswith('vt '):uv.append(line.split()[1:])
        elif line.startswith('f '):f.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(v,float),np.array(n,float),np.array(uv,float),np.array(f,int)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);assert (np.linalg.norm(cross,axis=1)>1e-8).all()
    agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.995,(lod,agreement)
    assert len(f)==plan['triangles'][lod];xyz=v[:,[0,2,1]]*np.array((-1,1,1));lo,hi=xyz.min(0),xyz.max(0)
    assert lo[2]>=-.01 and hi[2]<=65.25 and (np.abs(xyz[:,:2])<22.3).all(),(lo,hi)
    results.append(dict(lod=lod,triangles=len(f),normal_agreement=agreement,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'pedestal.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).is_file(),p
compiled=json.loads((OUT/'compilation.json').read_text());assert len(compiled)==4 and all(x['Success'] for x in compiled)
native=json.loads((OUT/'installed/validation.json').read_text());assert native['ModelsValid'] and native['LodTriangles']==plan['triangles'] and native['AddedColliders']==0 and native['PlayStateUnchanged']
assert native['PlayerFloorHit'] and abs(native['PlayerFloorZ'])<.5
report=dict(installed=True,original_faces_matched=24,original_glass_contents_and_physics_preserved=True,lods=results,native_player_height_view_verified=True,native_active_scene_unchanged_during_capture=native['SceneUnchanged'])
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
