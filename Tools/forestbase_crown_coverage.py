"""Choose complete source needle islands by multi-view alpha coverage.

The 16 orthographic analysis views are a geometry/atlas heuristic, not native
rendering or a performance benchmark. All retained charts keep source vertices,
UVs and normals. Far/horizon triangle budgets cannot exceed their old budgets.
"""
import argparse
from collections import defaultdict
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import shutil
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from PIL import Image
from forestbase_crown_obj import read_faces,write_faces

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Assets/models/maps/forestbase/fir'
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=ROOT/'output/forestbase/crown-stage/models/maps/forestbase/fir')
parser.add_argument('--legacy-input',type=Path,default=SOURCE,
                    help='Fixed pre-crown distant/horizon meshes; production import supplies freshly generated legacy meshes.')
parser.add_argument('--variants',nargs='+',choices=tuple('abc'),default=list('abc'))
parser.add_argument('--levels',nargs='+',choices=('distant','horizon'),default=['distant','horizon'])
parser.add_argument('--analysis-name',default='coverage-analysis.json')
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
W,H=256,512
FAR_LIMITS={'a':20443,'b':21347,'c':9900}
HORIZON_LIMITS={'a':4998,'b':5000,'c':5000}
NEEDLE='fir_tree_01_twig'
alpha=np.asarray(Image.open(SOURCE/'textures/twig_alpha_2k.png').convert('L'),dtype=np.float32)/255


def source_islands(path):
    verts=[];faces=[];paint=None
    for line in path.read_text().splitlines():
        f=line.split()
        if not f:continue
        if f[0]=='v':verts.append(tuple(map(float,f[1:])))
        elif f[0]=='usemtl':paint=f[1]
        elif f[0]=='f' and paint==NEEDLE:faces.append([int(v.split('/')[0])-1 for v in f[1:]])
    parents=list(range(len(verts)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for f in faces:
        for i in f[1:]:parents[find(i)]=find(f[0])
    groups=defaultdict(list)
    for i,f in enumerate(faces):groups[find(f[0])].append(i)
    return np.asarray(verts),np.asarray(faces),list(groups.values())


def projectors(verts):
    result=[]
    for elevation in (0,25):
        el=math.radians(elevation)
        for azimuth in range(0,360,45):
            az=math.radians(azimuth)
            right=np.array((math.cos(az),0,math.sin(az)))
            up=np.array((-math.sin(az)*math.sin(el),math.cos(el),math.cos(az)*math.sin(el)))
            matrix=np.stack((right,up),axis=1);p=verts@matrix
            lo,hi=p.min(axis=0),p.max(axis=0)
            scale=min((W-4)/(hi[0]-lo[0]),(H-4)/(hi[1]-lo[1]))
            shift=np.array((W,H))/2-(lo+hi)*scale/2
            result.append(dict(matrix=matrix,scale=scale,shift=shift,azimuth=azimuth,elevation=elevation))
    return result


def triangle_pixels(p,uv):
    low=np.maximum(np.floor(p.min(axis=0)).astype(int),0)
    high=np.minimum(np.ceil(p.max(axis=0)).astype(int),(W-1,H-1))
    if np.any(high<low):return np.empty(0,dtype=np.int32)
    a,b=p[1]-p[0],p[2]-p[0];det=a[0]*b[1]-a[1]*b[0]
    if abs(det)<1e-8:return np.empty(0,dtype=np.int32)
    xx,yy=np.meshgrid(np.arange(low[0],high[0]+1),np.arange(low[1],high[1]+1))
    dx,dy=xx+.5-p[0,0],yy+.5-p[0,1]
    u=(dx*b[1]-dy*b[0])/det;v=(a[0]*dy-a[1]*dx)/det
    inside=(u>=0)&(v>=0)&(u+v<=1)
    if not inside.any():return np.empty(0,dtype=np.int32)
    t=uv[0]+u[inside,None]*(uv[1]-uv[0])+v[inside,None]*(uv[2]-uv[0])
    x=np.mod(t[:,0],1)*(alpha.shape[1]-1);y=np.mod(1-t[:,1],1)*(alpha.shape[0]-1)
    x0,y0=x.astype(int),y.astype(int);fx,fy=x-x0,y-y0
    x1=np.minimum(x0+1,alpha.shape[1]-1);y1=np.minimum(y0+1,alpha.shape[0]-1)
    sampled=(alpha[y0,x0]*(1-fx)+alpha[y0,x1]*fx)*(1-fy)+(alpha[y1,x0]*(1-fx)+alpha[y1,x1]*fx)*fy
    return (yy[inside]*W+xx[inside])[sampled>=.25].astype(np.int32)


def masks_for_groups(verts,indices,rows,groups,cameras,variant):
    uv=np.array([[tuple(map(float,t.split())) for v,t,n in row] for row in rows])
    buckets=[[] for _ in groups]
    for view,camera in enumerate(cameras):
        projected=(verts@camera['matrix'])*camera['scale']+camera['shift']
        for k,ids in enumerate(groups):
            pieces=[triangle_pixels(projected[indices[i]],uv[i]) for i in ids]
            if pieces:
                values=np.unique(np.concatenate(pieces))
                if len(values):buckets[k].append(values+view*W*H)
        print(json.dumps(dict(variant=variant,phase='reference projection',view=view+1,total=len(cameras))),flush=True)
    return [np.unique(np.concatenate(b)) if b else np.empty(0,dtype=np.int32) for b in buckets]


def alpha_mask(rows,cameras):
    v=np.array([[tuple(map(float,p.split())) for p,t,n in row] for row in rows])
    uv=np.array([[tuple(map(float,t.split())) for p,t,n in row] for row in rows])
    mask=np.zeros(len(cameras)*W*H,dtype=bool)
    for view,camera in enumerate(cameras):
        p=(v@camera['matrix'])*camera['scale']+camera['shift']
        for tri,t in zip(p,uv):mask[triangle_pixels(tri,t)+view*W*H]=True
    return mask


def protected_islands(verts,indices,groups):
    points=[verts[np.unique(indices[ids])] for ids in groups]
    centers=np.array([(p.min(axis=0)+p.max(axis=0))/2 for p in points])
    lo,hi=centers[:,1].min(),centers[:,1].max();keep=set()
    for axis in range(3):
        keep.add(min(range(len(points)),key=lambda i:points[i][:,axis].min()))
        keep.add(max(range(len(points)),key=lambda i:points[i][:,axis].max()))
    bands=np.minimum(17,((centers[:,1]-lo)/(hi-lo)*18).astype(int))
    for band in range(18):
        candidates=np.flatnonzero(bands==band)
        if not len(candidates):continue
        for angle in np.linspace(0,math.tau,8,endpoint=False):
            direction=np.array((math.cos(angle),0,math.sin(angle)))
            keep.add(max(candidates,key=lambda i:float(np.max(points[i]@direction))))
    return keep


def select(groups,masks,protected,budget,cameras,reference):
    costs=[len(g) for g in groups]
    if sum(costs)<=budget:return set(range(len(groups)))
    keep=set(protected);used=sum(costs[i] for i in keep)
    assert used<=budget,('Protected crown exceeds budget',used,budget)
    covered=np.zeros(len(cameras)*W*H,dtype=bool)
    for i in keep:covered[masks[i]]=True
    queue=[(-len(masks[i])/costs[i],i) for i in range(len(groups)) if i not in keep]
    heapq.heapify(queue)
    while queue:
        upper,i=heapq.heappop(queue)
        if costs[i]>budget-used:continue
        fresh=masks[i][~covered[masks[i]]]
        gain=(np.count_nonzero(reference[fresh])-.7*np.count_nonzero(~reference[fresh]))/costs[i]
        if gain<=0:continue
        if queue and gain<-queue[0][0]-1e-12:
            heapq.heappush(queue,(-gain,i));continue
        keep.add(i);used+=costs[i];covered[masks[i]]=True
    # Retain additional depth/detail after the sampled silhouettes saturate.
    for i in sorted(range(len(groups)),key=lambda i:(-len(masks[i])/costs[i],i)):
        if i not in keep and used+costs[i]<=budget:keep.add(i);used+=costs[i]
    return keep


def summarize(mask,reference,cameras):
    result=[]
    for i,camera in enumerate(cameras):
        a=mask[i*W*H:(i+1)*W*H];b=reference[i*W*H:(i+1)*W*H]
        result.append(dict(azimuth=camera['azimuth'],elevation=camera['elevation'],pixels=int(a.sum()),
            referencePixels=int(b.sum()),referenceCoverage=float((a&b).sum()/max(b.sum(),1)),
            intersectionOverUnion=float((a&b).sum()/max((a|b).sum(),1))))
    return result


report=[]
for variant in args.variants:
    source=SOURCE/f'fir_{variant}_lod0.obj';near=read_faces(source)
    verts,indices,groups=source_islands(source)
    cameras=projectors(verts);masks=masks_for_groups(verts,indices,near[NEEDLE],groups,cameras,variant)
    reference=np.zeros(len(cameras)*W*H,dtype=bool)
    for mask in masks:reference[mask]=True
    protected=protected_islands(verts,indices,groups)
    medium=read_faces(args.output/f'fir_{variant}_lod1.obj')
    wood={p:rows for p,rows in medium.items() if p!=NEEDLE}
    for level,limit,opaque in [('distant',FAR_LIMITS[variant],wood),
        ('horizon',HORIZON_LIMITS[variant],{p:rows for p,rows in read_faces(args.legacy_input/f'fir_{variant}_horizon.obj').items() if p!=NEEDLE})]:
        if level not in args.levels:continue
        legacy_path=args.legacy_input/f'fir_{variant}_{level}.obj'
        baseline_rows=read_faces(legacy_path)[NEEDLE]
        level_rows,level_groups,level_masks,level_protected=near[NEEDLE],groups,masks,protected
        budget=limit-sum(len(f) for f in opaque.values())
        keep=select(level_groups,level_masks,level_protected,budget,cameras,reference)
        ids=sorted(i for g in keep for i in level_groups[g]);candidate=dict(opaque);candidate[NEEDLE]=[level_rows[i] for i in ids]
        after=np.zeros_like(reference)
        for i in keep:after[level_masks[i]]=True
        baseline=alpha_mask(baseline_rows,cameras)
        retained_legacy=False
        score=lambda m:float(np.mean([v['intersectionOverUnion'] for v in summarize(m,reference,cameras)]))
        if score(after)<score(baseline):
            assert level=='horizon','Far selection regressed'
            candidate=read_faces(legacy_path);after=baseline.copy();retained_legacy=True
        legacy_sha=hashlib.sha256(legacy_path.read_bytes()).hexdigest()
        assert score(after)>=score(baseline)-1e-10,('Sampled silhouette regression',variant,level)
        path=args.output/f'fir_{variant}_{level}.obj'
        if retained_legacy:
            if legacy_path.resolve()!=path.resolve():shutil.copyfile(legacy_path,path)
        else:write_faces(path,candidate)
        mtl=SOURCE/f'fir_{variant}_{level}.mtl'
        if mtl.resolve()!=path.with_suffix('.mtl').resolve():shutil.copyfile(mtl,path.with_suffix('.mtl'))
        entry=dict(variant=variant,level=level,triangles=sum(len(f) for f in candidate.values()),budget=limit,
            needleTriangles=len(candidate[NEEDLE]),sourceNeedleTriangles=len(near[NEEDLE]),islands=None if retained_legacy else len(keep),
            protectedIslands=None if retained_legacy else len(level_protected),
            retainedLegacy=retained_legacy,legacySourceSha256=legacy_sha,
            before=summarize(baseline,reference,cameras),after=summarize(after,reference,cameras),
            sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),outputSha256=hashlib.sha256(path.read_bytes()).hexdigest())
        report.append(entry)
        print(json.dumps(dict(variant=variant,level=level,triangles=entry['triangles'],
            coverageBefore=float(np.mean([r['referenceCoverage'] for r in entry['before']])),
            coverageAfter=float(np.mean([r['referenceCoverage'] for r in entry['after']])))),flush=True)
(args.output/args.analysis_name).write_text(json.dumps(dict(
    scope='Bilinear atlas-alpha geometry heuristic in 16 sampled orthographic views; no native shading, mip/LOD transition or FPS acceptance.',
    width=W,height=H,alphaThreshold=.25,textureSha256=hashlib.sha256((SOURCE/'textures/twig_alpha_2k.png').read_bytes()).hexdigest(),results=report),indent=2)+'\n')
