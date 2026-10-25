"""Low forest-bank relief and clustered, opaque geometry grass outside play.

Source vegetation is HC1's existing short grass, with its original UVs and
three geometry LODs. No bitmap generation, editor calls or collision changes.
"""
from functools import lru_cache
from pathlib import Path
import json
import math
import re

import numpy as np
import map_kit as K

RESOURCE = 'models/maps/forestbase/floor'
MATERIAL = 'materials/forestbase/forest_grass.vmat'
RECTS = (((-7000,-7000,-125),(-1550,7000,-120)),
         ((1550,-7000,-125),(7000,7000,-120)),
         ((-1550,1450,-125),(1550,2850,-120)),
         ((-1550,2850,-125),(-220,4150,-120)),
         ((1080,2850,-125),(1550,4150,-120)),
         ((-1550,4150,-125),(1550,7000,-120)),
         ((-1550,-7000,-125),(-550,-1450,-120)),
         ((550,-7000,-125),(1550,-1450,-120)))


def smooth(t):
    t = np.clip(t, 0, 1)
    return t*t*(3-2*t)


def offset(e,n):
    # Positive relief keeps existing tree roots buried rather than floating.
    wave = (1+math.sin(e/231+n/197)*math.cos(n/157-e/403))*.5
    detail = (1+math.sin(e/91-n/123))*.5
    depth = max(abs(e)-1550, n-1450, -1450-n, 0)
    basin = math.hypot(max(-220-e, e-1080, 0), max(2850-n, n-4150, 0))
    gorge = math.hypot(max(abs(e)-550, 0), max(n+1450, -7000-n, 0))
    border = min(7000-abs(e),7000-abs(n))
    return (9*wave+3*detail)*float(smooth(depth/300)*smooth(basin/180)*smooth(gorge/130)*smooth(border/256))


def knots(a,b,step=192):
    return [a]+[float(v) for v in np.arange(math.ceil((a+.001)/step)*step,b-.001,step)]+[b]


def bank_point(side,along,depth):
    edge = 1450 if side in (0,3) else 1550
    across = edge+depth
    e,n = ((along,across) if side==0 else (-across,along) if side==1 else
           (across,along) if side==2 else (along,-across))
    return np.array((e,n,-8-depth*112/300+offset(e,n)))


@lru_cache(None)
def surface():
    patches = []
    for lo,hi in RECTS:
        xs,ys = knots(lo[0],hi[0]),knots(lo[1],hi[1])
        for a,b in zip(xs,xs[1:]):
            for c,d in zip(ys,ys[1:]):
                xy = ((a,c),(b,c),(b,d),(a,d))
                points = np.array([(e,n,-120+offset(e,n)) for e,n in xy])
                normals=[]
                for e,n in xy:
                    dx=(offset(e+.1,n)-offset(e-.1,n))/.2
                    dy=(offset(e,n+.1)-offset(e,n-.1))/.2
                    normals.append(K.normalise((-dx,-dy,1)))
                patches.append((points,np.array(normals),'floor'))
    for side in range(4):
        along = sorted(set(np.linspace(-1550,1550,33)) | ({-620.,620.} if side==3 else set()))
        for a,b in zip(along,along[1:]):
            if side==3 and a<620 and b>-620:
                continue
            for c,d in zip(np.linspace(0,300,9),np.linspace(0,300,9)[1:]):
                coords = [(a,c),(b,c),(b,d),(a,d)]
                points = np.array([bank_point(side,x,y) for x,y in coords])
                normals=[]
                for x,y in coords:
                    u=bank_point(side,x+.1,y)-bank_point(side,x-.1,y)
                    v=bank_point(side,x,y+.1)-bank_point(side,x,y-.1)
                    normal=K.normalise(np.cross(u,v))
                    normals.append(normal if normal[2]>0 else -normal)
                if np.cross(points[1]-points[0],points[2]-points[0])[2]<0:
                    points=points[::-1];normals=normals[::-1]
                patches.append((points,np.array(normals),'bank'))
    return patches


@lru_cache(None)
def triangles():
    return np.array([points[list(ids)] for points,ns,kind in surface()
                     for ids in ((0,1,2),(0,2,3))])


@lru_cache(None)
def height(e,n):
    """Exact barycentric height on the generated top triangles, not the noise."""
    tris=triangles()
    mask=(tris[:,:,0].min(axis=1)-.001<=e)&(tris[:,:,0].max(axis=1)+.001>=e)
    mask&=(tris[:,:,1].min(axis=1)-.001<=n)&(tris[:,:,1].max(axis=1)+.001>=n)
    hits=[]
    for tri in tris[mask]:
        v,w=tri[1,:2]-tri[0,:2],tri[2,:2]-tri[0,:2]
        uv=np.linalg.solve(np.stack((v,w),axis=1),np.array((e,n))-tri[0,:2])
        if min(uv)>=-.00001 and sum(uv)<=1.00001:
            hits.append(float(tri[0,2]+uv[0]*(tri[1,2]-tri[0,2])+uv[1]*(tri[2,2]-tri[0,2])))
    assert hits, (e,n)
    return max(hits)


def build(m):
    if m.__class__.__name__=='CollisionOnlyModel':return
    for lo,hi in RECTS:
        m.box(lo,hi,'mud',skip=('+z',))
    for points,normals,kind in surface():
        m.polygon('mud',points,normals=normals)


def material(output=None):
    path=K.ASSETS/MATERIAL if output is None else Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    text=(K.ASSETS/'models/grass/grass_far.vmat').read_text()
    # Reuse HC1's foliage wrap/backlight and upward normal blend. Disable
    # origin-relative wind/rise for merged, terrain-conforming grass batches.
    values={'g_flSwayAmount':0,'g_flGustAmount':0,'g_flRiseStart':0,'g_flRiseEnd':0,
            'g_flFadeStart':40000,'g_flFadeEnd':50000,'g_flGrassNormalUp':.65}
    for key,value in values.items():
        text,count=re.subn(r'\b'+key+r'\s+"[^\"]+"',f'{key} "{value}"',text)
        assert count==1,key
    K.write_text(path,text)


@lru_cache(None)
def placements():
    rng=np.random.default_rng(372910)
    groups=[]
    for side in range(4):
        for half in range(2):
            plants=[]
            amin,amax=((-1400,-750) if half==0 else (750,1400)) if side==3 else ((-1400,-150) if half==0 else (150,1400))
            for cluster in range(8):
                along=float(rng.uniform(amin,amax));depth=float(rng.uniform(430 if side==3 else 140,620))
                for tuft in range(16):
                    a=along+float(rng.normal(0,33));d=depth+float(rng.normal(0,27))
                    if not 75<d<710:continue
                    p=bank_point(side,a,d)
                    if d>300:p[2]=-120
                    p[2]=height(*p[:2])-.25
                    scale=np.array((rng.uniform(.7,1.25),rng.uniform(.7,1.25),rng.uniform(.50,.95)))
                    plants.append((p,float(rng.uniform(0,math.tau)),scale))
            along=(amin+amax)/2;origin=bank_point(side,along,390);origin[2]=-120
            groups.append((side,half,origin,plants))
    return groups


def instances():
    return [(f'Forest floor grass {side} {half}',f'{RESOURCE}/grass_{side}_{half}.vmdl',
             tuple(origin),0,(1,1,1)) for side,half,origin,plants in placements()]


def source_grass(lod):
    vertices=[];uv=[];normals=[];faces=[]
    for line in (K.ASSETS/f'models/grass/grass_far_short_lod{lod}.obj').read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':vertices.append(tuple(map(float,f[1:4])))
        elif f[0]=='vt':uv.append(tuple(map(float,f[1:3])))
        elif f[0]=='vn':normals.append(tuple(map(float,f[1:4])))
        elif f[0]=='f':faces.append([tuple(int(i)-1 for i in v.split('/')) for v in f[1:]])
    vertices=np.asarray(vertices)[:,[0,2,1]];vertices[:,0]*=-1
    normals=np.asarray(normals)[:,[0,2,1]];normals[:,0]*=-1
    return vertices,uv,normals,faces


def write_models(output=None):
    output=K.ASSETS/RESOURCE if output is None else Path(output)
    output.mkdir(parents=True,exist_ok=True)
    stats={};anchors={}
    for side,half,origin,plants in placements():
        name=f'grass_{side}_{half}';lod_stats=[];anchors[name]=[]
        for lod in range(3):
            verts,uv,normals,faces=source_grass(lod)
            m=K.Model();m.material_overrides['forest_grass']=MATERIAL;m.tile_overrides['forest_grass']=64
            for p,yaw,scale in plants:
                c,s=math.cos(yaw),math.sin(yaw);rotation=np.array(((c,-s,0),(s,c,0),(0,0,1)))
                delta=(verts*scale)@rotation.T
                gradient=np.array(((height(p[0]+8,p[1])-height(p[0]-8,p[1]))/16,
                                   (height(p[0],p[1]+8)-height(p[0],p[1]-8))/16))
                delta[:,2]+=delta[:,:2]@gradient
                placed=delta+p-origin
                ns=(normals/scale)@rotation.T;ns/=np.linalg.norm(ns,axis=1,keepdims=True)
                ns[:,:2]-=ns[:,2,None]*gradient
                ns/=np.linalg.norm(ns,axis=1,keepdims=True)
                if lod==0:
                    roots=np.flatnonzero(np.abs(verts[:,2])<.0001)
                    ids=roots[[0,len(roots)//2,-1]]
                    anchors[name].extend((placed[ids]+origin).tolist())
                for face in faces:
                    m.polygon('forest_grass',[placed[v] for v,t,n in face],
                              uv=[uv[t] for v,t,n in face],normals=[ns[n] for v,t,n in face])
            K.write_model(output,RESOURCE,f'{name}_lod{lod}',m)
            lod_stats.append(m.triangle_count())
        text=(output/f'{name}_lod0.vmdl').read_text()
        begin=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
        end=text.index('\n\t\t]\n',begin)
        meshes='\t\t\t{ _class = "RenderMeshList" children = [\n'
        for lod in range(3):
            meshes+=f' {{ _class = "RenderMeshFile" name = "lod{lod}" filename = "{RESOURCE}/{name}_lod{lod}.obj" import_scale = 1.0 import_rotation = [0,0,0] import_translation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }},\n'
        meshes+=' ] },\n { _class = "LODGroupList" children = [\n'
        for lod,threshold in enumerate((0,110,170)):
            meshes+=f' {{ _class = "LODGroup" switch_threshold = {threshold}.0 meshes = ["lod{lod}"] }},\n'
        meshes+=' ] },'
        K.write_text(output/f'{name}.vmdl',text[:begin]+meshes+text[end:])
        stats[name]={'tufts':len(plants),'triangles':lod_stats}
    K.write_text(output/'placement-audit.json',json.dumps(anchors,indent=2)+'\n')
    return stats
