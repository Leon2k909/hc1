from pathlib import Path
import json,hashlib,re,collections,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/orion/undercroft-facade-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();folder=ROOT/'Assets/models/props/orion/undercroft_facade_v1'
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
original=(ROOT/'Assets/models/maps/orion/orion_launch_deck.obj').read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==50 and all(original[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(original) if i not in cut)
public=(ROOT/'Assets/models/maps/orion/orion_launch_deck.vmdl').read_text();preview=(folder/'preview.vmdl').read_text();assert preview.replace('models/props/orion/undercroft_facade_v1/preview.obj','models/maps/orion/orion_launch_deck.obj')==public
v=[];n=[];uv=[];faces=[];paints=[];paint=''
for l in (folder/'facade.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f':faces.append([[int(k)-1 for k in t.split('/')] for t in s[1:]]);paints.append(paint)
v=np.array(v);n=np.array(n);uv=np.array(uv);f=np.array(faces);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all() and (length>1e-10).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1,agreement
front=np.array([paint=='oa_wall' and np.allclose(pts[:,2],900) for paint,pts in zip(paints,p)])
area=float(length[front].sum()/2);expected=740*240-sum((b-a)*(d-c) for a,b,c,d in m['holes']);assert abs(area-expected)<.01,(area,expected)
# Original and replacement concrete use one continuous affine UV projection.
ov=[];ot=[];paint='';fitp=[];fituv=[]
for i,l in enumerate(original):
 s=l.split()
 if not s:continue
 if s[0]=='v':ov.append(tuple(map(float,s[1:])))
 elif s[0]=='vt':ot.append(tuple(map(float,s[1:])))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f' and i in cut and paint=='oa_wall':
  for t in s[1:]:
   a,b,c=(int(k)-1 for k in t.split('/'));pt=ov[a];fitp.append((-pt[0],pt[1],1));fituv.append(ot[b])
fit=np.linalg.lstsq(np.array(fitp),np.array(fituv),rcond=None)[0];fp=p[front];pred=np.stack((-fp[:,:,0],fp[:,:,1],np.ones_like(fp[:,:,0])),axis=-1)@fit;actual=uv[f[front,:,1]];uv_error=float(abs(pred-actual).max());assert uv_error<.00002,uv_error
# Visual rays independently prove the openings are recessed and not just raised frames.
e1=p[:,1]-p[:,0];e2=p[:,2]-p[:,0]
def ray(e,z):
 origin=np.array((-e,z,880.));direction=np.array((0.,0.,1.));h=np.cross(np.broadcast_to(direction,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);valid=abs(det)>1e-10;inv=np.divide(1.,det,out=np.zeros_like(det),where=valid);s=origin-p[:,0];u=np.einsum('ij,ij->i',s,h)*inv;q=np.cross(s,e1);vv=np.einsum('j,ij->i',direction,q)*inv;t=np.einsum('ij,ij->i',e2,q)*inv;good=valid&(u>=-1e-6)&(vv>=-1e-6)&(u+vv<=1.000001)&(t>0)
 assert good.any();return float(t[good].min()-20)
rays={}
for cx in (-500.,-250.):rays[f'door_{cx}']=ray(cx+15,85);assert abs(rays[f'door_{cx}']-7.1)<.02
for cx in (-380.,-130.):rays[f'window_{cx}']=ray(cx-14,77);assert abs(rays[f'window_{cx}']-8.25)<.02
rays['concrete']=ray(-315,140);assert abs(rays['concrete'])<.001
doc=(folder/'facade.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for path in re.findall(r'(?:filename|to)\s*=\s*"([^\"]+)"',doc):assert (ROOT/'Assets'/path).exists(),path
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==m['triangles'] and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['InteriorLights']==2
report=dict(review_only=True,old_cards_and_only_front_wall_removed=True,unrelated_obj_records_preserved=True,original_modeldoc_physics_preserved=True,public_scene_and_materials_unchanged=True,geometry_finite_nondegenerate=True,normal_agreement=agreement,front_wall_area_correct=True,visual_recess_depth_inches=rays,native=native)
report['concrete_texture_uv_max_error']=uv_error
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
