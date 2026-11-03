"""Close only the published terrain's open inner rim, retaining all existing faces."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import shutil
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/spillway/waterline-fix-v1'
STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_splice as splice

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text,encoding='utf-8',newline='')
    return p

asset='Assets/models/maps/spillway/spillway_mountains.obj'
tool='Tools/spillway_landscape.py'
protected=[ROOT/'Assets/scenes/maps/spillway/spillway.scene',*sorted((ROOT/'Assets/models/maps/spillway').glob('*'))]
protected=[p for p in protected if p.is_file() and p.suffix in ('.scene','.obj','.vmdl','.mtl')]
guards={p.relative_to(ROOT).as_posix():sha(p) for p in [ROOT/tool,*protected]}
for rel in (asset,tool):
    p=OUT/'before'/rel;p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert sha(p)==sha(ROOT/rel),'Baseline changed: '+rel
    else:shutil.copy2(ROOT/rel,p)

helper='''

def close_shoreline(model, rim_points, rim_normals):
    """Connect the visual terrain's open 3600-inch rim to a submerged bank.

    Leave the accepted terrain and forest positions intact. The lower edge is
    below the -245 river plane, outside the playable enclosure, and render-only.
    """
    rim_points=np.asarray(rim_points,float)
    rim_normals=np.asarray(rim_normals,float)
    radius=np.linalg.norm(rim_points[:,:2],axis=1)
    radial=rim_points[:,:2]/radius[:,None]
    angle=np.arctan2(radial[:,0],radial[:,1])
    inner=3180+55*np.sin(angle*7)+30*np.sin(angle*13+.8)
    rings=[]; normals=[]
    for t in np.linspace(0,1,7):
        r=inner+(radius-inner)*t
        z=-560+(rim_points[:,2]+560)*(2*t-t*t)
        slope=2*(rim_points[:,2]+560)*(1-t)/(radius-inner)
        normal=np.column_stack((-radial*slope[:,None],np.ones(len(radius))))
        normal/=np.linalg.norm(normal,axis=1)[:,None]
        rings.append(np.column_stack((radial*r[:,None],z)))
        normals.append(normal)
    # Exact seam positions and normals, including the existing waterfall carve.
    rings[-1]=rim_points.copy(); normals[-1]=rim_normals.copy()
    for i in range(len(rings)-1):
        for j in range(len(radius)):
            j1=(j+1)%len(radius)
            points=[rings[i][j],rings[i][j1],rings[i+1][j1],rings[i+1][j]]
            ns=[normals[i][j],normals[i][j1],normals[i+1][j1],normals[i+1][j]]
            P.card(model,"rv_forest",points,(0,0,1),normals=ns)
'''
old_tool=(ROOT/tool).read_text()
assert 'def close_shoreline(' not in old_tool
needle='    return radii, angles, h'
assert old_tool.count(needle)==1
new_tool=old_tool.replace(needle,'    close_shoreline(model, points[0], normals[0])\n'+needle)+helper
put(tool,new_tool)
ns={};exec(compile(new_tool,tool,'exec'),ns)
header,original=splice.read_obj(ROOT/asset)
rim={}
for paint,corners in original:
    for p,uv,n in corners:
        x,z,y=map(float,p.split())
        if abs(math.hypot(x,y)-3600)<.002:
            nx,nz,ny=map(float,n.split())
            rim[(x,z,y)]=((-x,y,z),(-nx,ny,nz))
assert len(rim)==576,f'Unexpected rim points: {len(rim)}'
rim=sorted(rim.values(),key=lambda item:math.atan2(item[0][0],item[0][1]))
points=np.array([p for p,n in rim]);normals=np.array([n for p,n in rim])
model=K.Model();ns['close_shoreline'](model,points,normals)
model.tile_overrides['rv_forest']=640
assert not model.hulls and not model.boxes
K.write_obj(OUT/'bank.obj',model,'spillway_mountains')
added=splice.read_obj(OUT/'bank.obj')[1]
assert len(added)==6912
target=STAGE/asset;target.parent.mkdir(parents=True,exist_ok=True)
splice.write_obj(target,header,original+added)
assert Counter(original)<=Counter(splice.read_obj(target)[1])

# Every upper rim segment is shared with the published terrain; every lower
# segment is submerged by315 inches. There is no open above-water boundary.
edges=Counter()
for paint,corners in added:
    positions=[p for p,uv,n in corners]
    for a,b in zip(positions,positions[1:]+positions[:1]):edges[tuple(sorted((a,b)))]+=1
boundary=[edge for edge,count in edges.items() if count==1]
top={p for paint,corners in original for p,uv,n in corners if abs(math.hypot(float(p.split()[0]),float(p.split()[2]))-3600)<.002}
assert len(boundary)==1152
assert all((a in top and b in top) or max(float(a.split()[1]),float(b.split()[1])) < -245 for a,b in boundary)
plan=dict(guards=guards,files={rel:sha(STAGE/rel) for rel in (asset,tool)},
          original_triangles=len(original),added_triangles=len(added),final_triangles=len(original)+len(added),
          original_faces_preserved=True,scene_unchanged=True,collision_unchanged=True,
          rim_samples=len(rim),open_above_water_edges=0,bank_bottom=-560,water_height=-245)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
