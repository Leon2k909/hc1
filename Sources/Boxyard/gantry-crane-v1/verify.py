"""Check the review crane and unchanged public Boxyard assets."""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/boxyard/gantry-crane-v1'
manifest={'triangles':[34660,21888,6188]}
scene=json.loads((ROOT/'Assets/scenes/maps/Boxyard/boxyard.scene').read_text())
nodes=[n for n in scene['GameObjects'] if n.get('Name','').startswith('Gantry Crane ')]
assert len(nodes)==3 and [n['Position'] for n in nodes]==['1650,1715,0','-1600,-1960,0','1950,-2450,0']
assert not (ROOT/'Assets/models/props/boxyard/gantry_crane_v1/review').exists()
folder=ROOT/'Assets/models/props/boxyard/gantry_crane_v1';results=[]
for lod in range(3):
    vs,ns,uvs,fs=[],[],[],[]
    for line in (folder/f'gantry_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):vs.append(line.split()[1:])
        if line.startswith('vn '):ns.append(line.split()[1:])
        if line.startswith('vt '):uvs.append(line.split()[1:])
        if line.startswith('f '):fs.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(vs,float),np.array(ns,float),np.array(uvs,float),np.array(fs,int)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)
    assert (area>1e-8).all(),f'LOD {lod} degenerate faces'
    agree=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agree>.995,(lod,agree)
    assert len(f)==manifest['triangles'][lod]
    plan=v[:,[0,2,1]]*np.array((-1,1,1));lo,hi=plan.min(0),plan.max(0)
    assert lo[2]>=-.1 and hi[2]<840 and (np.abs(plan[:,:2])<530).all()
    results.append(dict(lod=lod,triangles=len(f),normal_agreement=agree,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'gantry.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for ref in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/ref).exists(),ref
comp=json.loads((OUT/'compilation.json').read_text());assert len(comp)==11 and all(c['Success'] for c in comp)
report=dict(installed=3,old_review_deleted=True,lods=results,compiled_resources=len(comp))
(OUT/'installed-geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
