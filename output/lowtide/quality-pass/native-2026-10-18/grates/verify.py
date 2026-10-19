import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_grates as G
import map_kit as K
import lowtide_window_construction as W

OUT = Path(__file__).resolve().parent


def triangles(path, material=None):
    vertices, result, paint = [], [], None
    for line in path.read_text().splitlines():
        s=line.split()
        if not s: continue
        if s[0]=='v':
            x,y,z=map(float,s[1:]); vertices.append((-x,z,y))
        elif s[0]=='usemtl': paint=s[1]
        elif s[0]=='f' and (material is None or paint==material):
            result.append([vertices[int(v.split('/')[0])-1] for v in s[1:]])
    return np.asarray(result)


def ray_z(tris,e,n):
    # Independent vertical ray/triangle intersection on exported, rounded OBJ.
    a,b,c=tris[:,0],tris[:,1],tris[:,2]
    v0,v1=b[:,:2]-a[:,:2],c[:,:2]-a[:,:2]
    v2=np.array([e,n])-a[:,:2]
    det=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]
    good=np.abs(det)>1e-8
    u=np.divide(v2[:,0]*v1[:,1]-v2[:,1]*v1[:,0],det,out=np.full_like(det,-1),where=good)
    v=np.divide(v0[:,0]*v2[:,1]-v0[:,1]*v2[:,0],det,out=np.full_like(det,-1),where=good)
    good &= (u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)
    z=a[:,2]+u*(b[:,2]-a[:,2])+v*(c[:,2]-a[:,2])
    return max(z[good],default=-np.inf)


surface=triangles(OUT/'grates-new.obj')
pavement={side:triangles(OUT/f'stage/Assets/models/maps/lowtide/lowtide_{side}.obj','setts') for side in ('east','west')}
checks=[]
for e,n,w,l in G.layout():
    near=surface[np.all(np.abs(surface[:,:,:2]-[e,n])<[w/2+2,l/2+2],axis=(1,2))]
    # A slot between bars must reveal the floor of the well ten inches below.
    usable=w-.7-2*.74
    count=max(5,round(usable/2.05))
    slot_e=e-usable/2+usable/count
    bar_e=e-usable/2+.5*usable/count
    slot_z=ray_z(near,slot_e,n+1)
    bar_z=ray_z(near,bar_e,n+1)
    assert abs(slot_z+10)<.002,(e,n,slot_z)
    assert abs(bar_z-.07)<.002,(e,n,bar_z)
    stone=pavement['east' if e>0 else 'west']
    for dx in (-w*.35,0,w*.35):
        for dy in (-l*.35,0,l*.35):
            assert ray_z(stone,e+dx,n+dy)<-.01,(e,n,dx,dy,'paving blocks hole')
    checks.append(dict(e=e,n=n,slot_depth=slot_z,bar_top=bar_z))
# Confirm canonical generation retains supporting collision while cutting render
# polygons. The exact full ground contour tests every authored grate placement.
m=K.Model()
m.box((-2800,-1700,-16),(2800,1500,0),'setts',surface='concrete')
collision=m.boxes.copy()
G.cut_model(m)
assert len(m.boxes)==len(collision)
assert all(np.array_equal(a,b) for a,b in zip(m.boxes[0][:3],collision[0][:3]))
top_area=sum(G.area(np.array(points)) for points,normal in m.polygons['setts'] if normal[2]>.99)
expected=5600*3200-sum((w+.2)*(l+.4) for e,n,w,l in G.layout())
assert abs(top_area-expected)<.01,(top_area,expected)
W.validate_model(m)
manifest=json.loads((OUT/'manifest.json').read_text())
assert all(G.sha(ROOT/path)==h for path,h in manifest['live_before'].items()),'Live resources changed before integration'
report=dict(grates=24,slot_and_bar_rays=48,pavement_aperture_rays=216,
            canonical_pavement_area=top_area,canonical_collision_preserved=True,
            exported_checks=checks,live_before_verified=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='exported_checks'},indent=2))
