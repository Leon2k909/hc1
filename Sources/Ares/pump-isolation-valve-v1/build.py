"""Private fitted valve on one existing vertical pump feed; original map stays active."""
from pathlib import Path
import sys,json,re,hashlib,shutil,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A,map_kit as K
OUT=ROOT/'output/ares/pump-isolation-valve-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/pump_isolation_valve_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();F=A.Frame(270,270,135);center=F.p(-20,0,92);low,high=92-16.64,92+16.64
docpath=ROOT/'Assets/models/maps/ares/ares_reactor.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
def clip(poly,z,keep_lower):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ina=a[0][2]<=z+1e-8 if keep_lower else a[0][2]>=z-1e-8
  inb=b[0][2]<=z+1e-8 if keep_lower else b[0][2]>=z-1e-8
  if ina:out.append(a)
  if ina!=inb:
   t=(z-a[0][2])/(b[0][2]-a[0][2]);out.append(tuple(x+(y-x)*t for x,y in zip(a,b)))
 clean=[]
 for p in out:
  if not clean or np.linalg.norm(p[0]-clean[-1][0])>1e-7:clean.append(p)
 if len(clean)>1 and np.linalg.norm(clean[0][0]-clean[-1][0])<1e-7:clean.pop()
 return clean
for rel in imports:
 lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);v=[];uv=[];n=[];paint='';cut=[];retained=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':a,z,north=map(float,s[1:]);v.append(np.array((-a,north,z)))
  elif s[0]=='vt':uv.append(np.array(list(map(float,s[1:]))))
  elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append(np.array((-a,north,z)))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f' and paint=='ar_in_alloy':
   ids=[[int(k)-1 for k in t.split('/')] for t in s[1:]];p=np.array([v[x] for x,t,z in ids]);r=np.linalg.norm(p[:,:2]-center[:2],axis=1)
   if p[:,2].min()<high and p[:,2].max()>low and p[:,2].min()>=63.99 and p[:,2].max()<134 and r.max()<6.02:
    cut.append(i);poly=[(v[x],uv[t],n[z]) for x,t,z in ids]
    for below,z in ((True,low),(False,high)):
     clipped=clip(poly,z,below)
     for j in range(1,len(clipped)-1):
      tri=[clipped[0],clipped[j],clipped[j+1]];ps=[x[0] for x in tri]
      if np.linalg.norm(np.cross(ps[1]-ps[0],ps[2]-ps[0]))>1e-10:retained.append(tri)
 if cut:matches.append((rel,lines,cut,retained,len(v),len(uv),len(n)))
assert len(matches)==1 and len(matches[0][2])==32,[(p,len(c)) for p,l,c,r,v,t,n in matches]
rel,lines,cut,retained,nv,nt,nn=matches[0];extra=['\n# Fitted valve: retained lower and upper original pipe surfaces\n','usemtl ar_in_alloy\n']
for tri in retained:
 tokens=[]
 for p,tex,normal in tri:
  normal=normal/np.linalg.norm(normal);nv+=1;nt+=1;nn+=1
  extra.extend([f'v {-p[0]:.8f} {p[2]:.8f} {p[1]:.8f}\n',f'vt {tex[0]:.9f} {tex[1]:.9f}\n',f'vn {-normal[0]:.9f} {normal[2]:.9f} {normal[1]:.9f}\n']);tokens.append(f'{nv}/{nt}/{nn}')
 extra.append('f '+' '.join(tokens)+'\n')
(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in set(cut))+''.join(extra))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
# Reuse the actual approved, already-compiled valve without duplicating its mesh.
valve='models/props/collider/valve-trial-v1/after.vmdl';valve_doc=ROOT/'Assets'/valve
outward=np.array((2**-.5,2**-.5,0));up=np.array((0.,0.,1.));T=np.column_stack((up,-outward,np.cross(up,-outward)));translation=K.to_world(center-T@np.array((0,0,13.)))
S=np.array(((0,1,0),(-1,0,0),(0,0,1)));rotation=S@T@S.T
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports],valve_doc,ROOT/'Assets/models/props/collider/valve-trial-v1/after.obj']
for material in re.findall(r'to\s*=\s*"([^"]+)"',valve_doc.read_text()):
 path=ROOT/'Assets'/material;protected.append(path)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',path.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,reused_approved_compiled_valve=valve,active_base=rel,pipe_plan_center=center.tolist(),cut_interval=[low,high],original_pipe_faces=len(cut),retained_pipe_triangles=len(retained),cut=cut,world_position=translation.tolist(),world_forward=rotation[:,0].tolist(),world_up=rotation[:,2].tolist(),world_valve_center=K.to_world(center).tolist(),world_wheel_center=K.to_world(center+25*outward).tolist(),protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected','files','cut')}))
