from pathlib import Path
import json,hashlib,re
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/radome-v1';plan=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in plan['protected'].items():assert sha(ROOT/p)==h,f'Public file changed: {p}'
for p,h in plan['files'].items():
    assert sha(OUT/'stage/Assets'/p)==h
    assert sha(ROOT/'Assets'/p)==h
folder=OUT/'stage/Assets/models/props/orion/radome_v1';results=[]
for lod in range(3):
    v,n,uv,f=[],[],[],[]
    for line in (folder/f'radome_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):v.append(line.split()[1:])
        elif line.startswith('vn '):n.append(line.split()[1:])
        elif line.startswith('vt '):uv.append(line.split()[1:])
        elif line.startswith('f '):f.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(v,float),np.array(n,float),np.array(uv,float),np.array(f,int)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);areas=np.linalg.norm(cross,axis=1);assert (areas>1e-8).all(),(lod,int(sum(areas<=1e-8)))
    agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.995,(lod,agreement)
    assert len(f)==plan['triangles'][lod]
    xyz=v[:,[0,2,1]]*np.array((-1,1,1));lo,hi=xyz.min(0),xyz.max(0)
    assert lo[2]>=-.01 and hi[2]<=785 and (np.abs(xyz[:,:2])<=341).all(),(lo,hi)
    results.append(dict(lod=lod,triangles=len(f),normals_agree=agreement,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'radome.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).exists() or (OUT/'stage/Assets'/p).exists(),p
report=dict(preview_only=True,published_map_unchanged=True,before_triangles=plan['before_triangles'],lods=results)
audit=json.loads((OUT/'existing-model-audit.json').read_text());assert audit['baseline_matches_actual_map'] and audit['current_baked_faces_matched']==1812
native=json.loads((OUT/'studio/validation.json').read_text());assert native['ModelsValid'] and native['Lods']==3 and native['SceneUnchanged'] and native['PlayStateUnchanged']
assert native['LodTriangles']==plan['triangles'],native['LodTriangles']
compiled=json.loads((OUT/'compilation.json').read_text());assert len(compiled)==7 and all(x['Success'] for x in compiled)
report.update(existing_models_checked=True,baseline_matches_actual_map=True,native_lods_verified=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
