from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/reefhall/display-coral-v1';plan=json.loads((OUT/'manifest.json').read_text());baseline=json.loads((OUT/'baseline.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in plan['protected'].items():assert sha(ROOT/p)==h,f'Public source changed: {p}'
for p,h in plan['files'].items():
    assert sha(OUT/'stage/Assets'/p)==h
    assert sha(ROOT/'Assets'/p)==h
folder=OUT/'stage/Assets/models/props/reefhall/display_coral_v1';lines=(ROOT/baseline['source']).read_text().splitlines();cut=set(baseline['face_lines']);assert len(cut)==288
assert (folder/'preview.obj').read_text().splitlines()==[line for i,line in enumerate(lines) if i not in cut]
results=[]
for lod in range(3):
    v,n,uv,f=[],[],[],[]
    for line in (folder/f'coral_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):v.append(line.split()[1:])
        elif line.startswith('vn '):n.append(line.split()[1:])
        elif line.startswith('vt '):uv.append(line.split()[1:])
        elif line.startswith('f '):f.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(v,float),np.array(n,float),np.array(uv,float),np.array(f,int);assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);assert (np.linalg.norm(cross,axis=1)>1e-8).all(),(lod,int(sum(np.linalg.norm(cross,axis=1)<=1e-8)))
    agree=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agree>.995,(lod,agree)
    assert len(f)==plan['triangles'][lod];world=v[:,[2,0,1]]+np.array(plan['position_world']);planxyz=world[:,[1,0,2]]*np.array((-1,1,1));lo,hi=planxyz.min(0),planxyz.max(0)
    assert (lo>=np.array(plan['original_bounds'][0])-.002).all() and (hi<=np.array(plan['original_bounds'][1])+.002).all(),(lo,hi)
    results.append(dict(lod=lod,triangles=len(f),normal_agreement=agree,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'coral.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for path in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/path).exists() or (OUT/'stage/Assets'/path).exists(),path
report=dict(preview_only=True,original_faces=288,all_other_aquarium_contents_identical=True,public_scene_and_models_unchanged=True,existing_occupied_envelope_preserved=True,lods=results)
compiled=json.loads((OUT/'compilation.json').read_text());assert len(compiled)==2 and all(x['Success'] for x in compiled)
if (OUT/'native/validation.json').exists():
    native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['LodTriangles']==plan['triangles'] and native['AddedColliders']==0 and native['PlayStateUnchanged'];report['native_lods_verified']=True
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
