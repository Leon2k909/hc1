"""Deterministic capsule-clearance and connectivity audit from the actual generated collision.
8-inch raster; radius 16, height 72, steps <=18. Conservative hull AABBs.
Complements engine traces and engine navmesh tests; does not claim to replace a multiplayer playtest.
"""
import json, os
from collections import deque
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
import forestbase_map as F
import map_kit as K

def audit():
    # Connectivity uses authored boxes/hulls only; avoid allocating every
    # visual triangle during the collision audit.
    models=F.build(visual_chunks=[])
    obstacles=[]; supports=[]
    for m in models.values():
        for c,axes,size,s in m.boxes:
            c=np.asarray(c,dtype=np.float32); axes=np.asarray(axes,dtype=np.float32); size=np.asarray(size,dtype=np.float32)
            ext=np.abs(axes).T@(size/2)
            obstacles.append((c-ext,c+ext,c,axes,size))
            if abs(axes[2,2])>.999 and c[2]+size[2]/2<=430:
                supports.append((c,axes,size,float(c[2]+size[2]/2)))
        for pts,s in m.hulls:
            pts=np.asarray(pts,dtype=np.float32); lo,hi=pts.min(0),pts.max(0)
            obstacles.append((lo,hi,(lo+hi)/2,np.eye(3,dtype=np.float32),hi-lo))
    xs=np.arange(-1544,1550,8,dtype=np.float32); ys=np.arange(-1704,1450,8,dtype=np.float32)
    heights=sorted({round(z,3) for c,a,s,z in supports if z>=0})
    h,w=len(ys),len(xs); n=h*w
    X,Y=np.meshgrid(xs,ys)
    walk=np.zeros((len(heights),h,w),bool)
    index={v:i for i,v in enumerate(heights)}
    for c,axes,size,z in supports:
        dx,dy=X-c[0],Y-c[1]
        u=dx*axes[0,0]+dy*axes[0,1]; v=dx*axes[1,0]+dy*axes[1,1]
        walk[index[round(z,3)]] |= (abs(u)<=size[0]/2+.01)&(abs(v)<=size[1]/2+.01)
    for lo,hi,c,axes,size in obstacles:
    # OBB exact plan test for horizontal boxes; expanded by capsule radius.
        if abs(axes[2,2])>.999:
            dx,dy=X-c[0],Y-c[1]
            footprint=(abs(dx*axes[0,0]+dy*axes[0,1])<size[0]/2+16)&(abs(dx*axes[1,0]+dy*axes[1,1])<size[1]/2+16)
        else:
            # Inclined handrails cannot be treated as their entire tall AABB:
            # that incorrectly blocks the deck under the high end of a roof stair.
            dx,dy=X-c[0],Y-c[1]
            player_half=np.array((16,16,27),dtype=np.float32)
            expansion=np.abs(axes)@player_half
            for i,z in enumerate(heights):
                if hi[2]<=z+18+.8 or lo[2]>=z+72-.8: continue
                dz=z+45-c[2]
                overlap=np.ones_like(X,dtype=bool)
                for k,axis in enumerate(axes):
                    overlap &= abs(dx*axis[0]+dy*axis[1]+dz*axis[2]) < size[k]/2+expansion[k]
                walk[i] &= ~overlap
            continue
        for i,z in enumerate(heights):
            # Movement can step over up to 18-inch risers; these must not be treated as headroom blockers.
            if hi[2]>z+18+.8 and lo[2]<z+72-.8: walk[i] &= ~footprint
    # Closed map perimeter, including the narrowed entrance spur.
    inside=(Y>=-1450)|((abs(X)<164)&(Y>=-1690))
    walk &= inside[None,:,:]
    def node(p):
        e,nn,z=p; row=int(round((nn-ys[0])/8)); col=int(round((e-xs[0])/8))
        levels=np.argsort(np.abs(np.array(heights)-z))
        for lev in levels:
            if abs(heights[lev]-z)<=18 and 0<=row<h and 0<=col<w and walk[lev,row,col]: return lev*n+row*w+col
        return None
    near=[np.flatnonzero(abs(np.array(heights)-z)<=18+.01).tolist() for z in heights]
    seen=np.zeros(walk.size,bool); flat=walk.ravel(); seed=node(F.RED[0]); queue=deque([seed]) if seed is not None else deque()
    if seed is not None: seen[seed]=True
    while queue:
        item=queue.popleft(); lev,cell=divmod(item,n); row,col=divmod(cell,w)
        for dr,dc in ((-1,0),(1,0),(0,-1),(0,1)):
            rr,cc=row+dr,col+dc
            if not (0<=rr<h and 0<=cc<w): continue
            for ll in near[lev]:
                nxt=ll*n+rr*w+cc
                if flat[nxt] and not seen[nxt]: seen[nxt]=True; queue.append(nxt)
    points=[(f'Red {i}',p) for i,p in enumerate(F.RED)]+[(f'Blue {i}',p) for i,p in enumerate(F.BLUE)]+[(f'DM {i}',p) for i,p in enumerate(F.DM)]
    points += [(f'Domination {l}',p) for l,p in F.OBJECTIVES]
    points += [('Barracks lower',(-1050,770,96)),('Barracks upper',(-1050,770,240)),('Command lower',(100,850,96)),
               ('Command upper',(100,850,240)),('Command roof',(250,840,384)),('Workshop',(1110,320,0)),
               ('Bridge west',(-330,880,240)),('Bridge east',(840,920,240))]
    points += [('Barracks west lower room',(-1100,980,96)),('Barracks west upper room',(-1100,980,240)),
               ('Barracks east lower room',(-850,990,96)),('Barracks east upper room',(-850,990,240)),
               ('Command west lower room',(95,1010,96)),('Command west upper room',(95,1010,240)),
               ('Command east lower room',(350,1010,96)),('Command east upper room',(350,1010,240)),
               ('Roof west approach',(-30,1183,258)),('Roof west stair midpoint',(120,1183,320)),
               ('Roof stair landing',(265,1183,384)),('Roof rear deck',(265,1100,384))]
    for route in F.ROUTES:
        if route['kind']!='stairs' or route['end'][2]!=384: continue
        a,b=np.array(route['start']),np.array(route['end'])
        count=int(np.ceil(abs(b[2]-a[2])/8))
        points += [(f'Roof stair {a[0]} step {k}',tuple(a+(b-a)*np.array(((k+.5)/count,(k+.5)/count,(k+1)/count)))) for k in range(count)]
    result=[]
    for name,p in points:
        candidate=node(p); result.append(dict(name=name,position=p,clear=candidate is not None,reachable=candidate is not None and bool(seen[candidate])))
    report=dict(grid=8,radius=16,height=72,step=18,reachableCells=int(seen.sum()),checks=result,problems=[r for r in result if not r['reachable']])
    folder=K.ROOT/'output/forestbase'; folder.mkdir(parents=True,exist_ok=True)
    K.write_text(folder/'route-audit.json',json.dumps(report,indent=2))
    img=np.zeros((h,w,3),dtype='uint8')+25
    img[walk.any(0)]=(86,76,53); img[seen.reshape(walk.shape).any(0)]=(78,145,117)
    Image.fromarray(img[::-1]).resize((w*2,h*2)).save(folder/'reachability.png')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
    return report

if __name__=='__main__': audit()
