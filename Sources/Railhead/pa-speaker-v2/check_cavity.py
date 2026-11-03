"""Check the saved mesh occludes the background behind corner perforations."""
from pathlib import Path
import json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/pa-speaker-v2'
lines=(OUT/'stage/Assets/models/maps/railhead/pa-speaker-v2/pa_speaker.obj').read_text().splitlines()
v=np.array([list(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')])
f=np.array([[int(t.split('/')[0])-1 for t in l.split()[1:]] for l in lines if l.startswith('f ')])
assert f.shape[1]==3
tri=v[f];e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
X=np.array((0.,1.,0.));N=np.array((math.cos(.35),0.,-math.sin(.35)));U=np.cross(N,X);C=np.array((14.1,820.,213.4))
def obj(p):e,n,z=p;return np.array((-e,z,n))
views=[np.array((813.,-43.,205.)),np.array((794.,-35.,213.))]
results=[]
edge_holes=[(i,j) for j in range(22) for i in range(36-(j%2)) if i in (0,35-(j%2)) or j in (0,21)]
for eye in views:
 origin=np.array((eye[1],eye[2],eye[0]))
 for i,j in edge_holes:
   x=-5.25+(i+.5+(j%2)*.5)*(10.5/36);u=-3.2+(j+.5)*(6.4/22)
   target=obj(C+X*x+N*3.005+U*u);distance=np.linalg.norm(target-origin);ray=(target-origin)/distance
   p=np.cross(np.broadcast_to(ray,e2.shape),e2);det=np.einsum('ij,ij->i',e1,p)
   # Count only front-facing triangles, matching ordinary renderer culling.
   valid=det>1e-9;inv=np.divide(1.,det,out=np.zeros_like(det),where=valid)
   t=origin-tri[:,0];uu=np.einsum('ij,ij->i',t,p)*inv;q=np.cross(t,e1)
   vv=np.einsum('j,ij->i',ray,q)*inv;hit=np.einsum('ij,ij->i',e2,q)*inv
   good=valid&(uu>=-1e-6)&(vv>=-1e-6)&(uu+vv<=1.000001)&(hit>distance+.005)&(hit<distance+15)
   assert good.any(),dict(eye=eye.tolist(),hole=(x,u),error='No cabinet surface behind hole')
   results.append(dict(eye=eye.tolist(),hole=(x,u),backing_depth=float(hit[good].min()-distance)))
(OUT/'cavity-check.json').write_text(json.dumps(dict(edge_hole_rays_checked=len(results),all_occluded=True,results=results),indent=2))
print(json.dumps(dict(edge_hole_rays_checked=len(results),all_occluded=True)))
