"""Verify the installed launch vehicle and the regenerating source hook."""
from pathlib import Path
import json,hashlib,re,sys
import numpy as np
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/launch-vehicle-v1';manifest=json.loads((OUT/'build-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((OUT/'installed-verification.json').read_text());assert proof['old_faces_removed']==1164 and proof['all_other_faces_and_attributes_identical']
plan=json.loads((OUT/'install-plan.json').read_text());assert sha(ROOT/'Assets/models/maps/orion/orion_pad.vmdl')==plan['protected']['Assets/models/maps/orion/orion_pad.vmdl']
for p,h in manifest['files'].items():assert sha(OUT/'stage/Assets'/p)==h and sha(ROOT/'Assets'/p)==h,p
assert not (ROOT/'Assets/models/props/orion/launch_vehicle_v1/review').exists()
scene=json.loads((ROOT/'Assets/scenes/maps/Orion/orion.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Orion Launch Vehicle'];assert len(nodes)==1
node=nodes[0];assert node['Position']=='2800,-694,240' and len(node['Components'])==1 and node['Components'][0]['Model']=='models/props/orion/launch_vehicle_v1/vehicle.vmdl'
sys.path.insert(0,str(ROOT/'Tools'));import orion_parts as O;import orion_launch_vehicle as V;import orion_map as R;import map_kit as K
O.reset();old=K.Model();O.rocket(old,(*R.ROCKET,R.ROCKET_Z),R.ROCKET_H,R.ROCKET_R,32,(-.25,-1));assert not old.polygons and len(O.LAUNCH_VEHICLES)==1
generated=V.objects(R.ids,O.LAUNCH_VEHICLES);assert len(generated)==1 and generated[0]['Position']==node['Position'] and generated[0]['Components'][0]['Model']==node['Components'][0]['Model']
folder=ROOT/'Assets/models/props/orion/launch_vehicle_v1';results=[]
for lod in range(3):
    v,n,uv,f=[],[],[],[]
    for line in (folder/f'vehicle_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):v.append(line.split()[1:])
        elif line.startswith('vn '):n.append(line.split()[1:])
        elif line.startswith('vt '):uv.append(line.split()[1:])
        elif line.startswith('f '):f.append([[int(x)-1 for x in t.split('/')] for t in line.split()[1:]])
    v,n,uv,f=np.array(v,float),np.array(n,float),np.array(uv,float),np.array(f,int)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    tri=v[f[:,:,0]];cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1);assert (area>1e-8).all()
    agree=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agree>.995,(lod,agree)
    assert len(f)==manifest['triangles'][lod]
    plan=v[:,[0,2,1]]*np.array((-1,1,1));lo,hi=plan.min(0),plan.max(0)
    assert lo[2]>=-27 and hi[2]<=1300.01 and (np.abs(plan[:,:2])<=126).all(),(lo,hi)
    results.append(dict(lod=lod,triangles=len(f),normal_agreement=agree,bounds=[lo.tolist(),hi.tolist()]))
doc=(folder/'vehicle.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
report=dict(installed=True,old_faces_removed=1164,source_geometry_reproduced=True,source_instance_verified=True,no_added_collision=True,lods=results)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
