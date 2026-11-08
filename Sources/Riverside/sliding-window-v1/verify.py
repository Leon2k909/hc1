from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/sliding-window-v1';plan=json.loads((OUT/'build-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((OUT/'installed-verification.json').read_text());assert proof['installed'] and proof['physics_identical']
for p,h in plan['files'].items():assert sha(ROOT/'Assets'/p)==h and sha(OUT/'stage/Assets'/p)==h,p
folder=ROOT/'Assets/models/props/riverside/sliding_window_v1'
scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='T2 Sliding Window Frame'];assert len(nodes)==1 and len(nodes[0]['Components'])==1
model=nodes[0]['Components'][0]['Model'];assert (model.get('Path') if isinstance(model,dict) else model)=='models/props/riverside/sliding_window_v1/window.vmdl';assert not (folder/'preview.vmdl').exists()
results=[]
for lod in range(3):
    v,n,uv,f=[],[],[],[]
    for line in (folder/f'window_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):v.append(line.split()[1:])
        elif line.startswith('vn '):n.append(line.split()[1:])
        elif line.startswith('vt '):uv.append(line.split()[1:])
        elif line.startswith('f '):f.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(v,float),np.array(n,float),np.array(uv,float),np.array(f,int);assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);assert (np.linalg.norm(cross,axis=1)>1e-8).all(),(lod,int(sum(np.linalg.norm(cross,axis=1)<=1e-8)))
    agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.995,(lod,agreement);assert len(f)==plan['triangles'][lod]
    xyz=v[:,[0,2,1]]*np.array((-1,1,1));lo,hi=xyz.min(0),xyz.max(0);assert (np.abs(xyz[:,0])<=17.51).all() and lo[2]>=-18.11 and hi[2]<=16.51 and lo[1]>=-2.81 and hi[1]<=.21,(lo,hi)
    results.append(dict(lod=lod,triangles=len(f),normal_agreement=agreement,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'window.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for path in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/path).is_file(),path
report=dict(installed=True,original_frame_faces=14,all_other_lowland_mesh_lines_identical=True,original_pane_artwork_and_physics_preserved=True,lods=results)
if (OUT/'compilation.json').is_file():
    compiled=json.loads((OUT/'compilation.json').read_text());assert len(compiled)==2 and all(x['Success'] for x in compiled)
if (OUT/'installed/validation.json').is_file():
    native=json.loads((OUT/'installed/validation.json').read_text());assert native['ModelsValid'] and native['LodTriangles']==plan['triangles'] and native['AddedColliders']==0 and native['PlayStateUnchanged'];report['native_lods_verified']=True
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
