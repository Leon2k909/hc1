"""Verify approved geometry survives native coordinates and the routed pipes clear each other."""
from pathlib import Path
from collections import Counter
import json,struct,sys,math
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1';OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
sys.path.insert(0,str(ROOT/'Tools'));import riverdale_parts as P
from riverdale_pipe_clearance import perimeter_path
raw=(HERE/'lifebuoy_after.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);binary=raw[28+n:]
def access(i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    kind={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']];size=np.dtype(kind).itemsize;offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    return np.ndarray((a['count'],width),dtype=kind,buffer=binary,offset=offset,strides=(v.get('byteStride',width*size),size)).copy()
glb_vertices=np.concatenate([access(p['attributes']['POSITION']) for p in doc['meshes'][0]['primitives']])/.0254
path=OUT/'install-stage/Assets/models/maps/riverdale/lifebuoy_v2/lifebuoy_lod0.obj';vs=[];ns=[];uv=[];paint='';faces=Counter();bad_winding=0
for line in path.open():
    p=line.split()
    if not p:continue
    if p[0]=='v':vs.append(list(map(float,p[1:])))
    elif p[0]=='vn':ns.append(list(map(float,p[1:])))
    elif p[0]=='vt':uv.append(list(map(float,p[1:])))
    elif p[0]=='usemtl':paint=p[1]
    elif p[0]=='f':
        refs=[[int(v)-1 for v in a.split('/')] for a in p[1:]];assert len(refs)==3 and paint.startswith('rv_lb_')
        pos=np.array([vs[v] for v,t,n in refs]);normal=np.mean([ns[n] for v,t,n in refs],axis=0)
        cross=np.cross(pos[1]-pos[0],pos[2]-pos[0]);assert np.linalg.norm(cross)>1e-12
        if cross@normal<-.000001:bad_winding+=1
        faces[paint]+=1
vs=np.array(vs);assert np.isfinite(vs).all() and np.isfinite(ns).all() and np.isfinite(uv).all()
error=max(cKDTree(vs).query(glb_vertices)[0].max(),cKDTree(glb_vertices).query(vs)[0].max())
assert error<.0001 and sum(faces.values())==42468 and bad_winding==0,(error,bad_winding)

def sample(path,r):
    points=P._bend_points(P._dedupe(path),r*1.5,max_step=3)
    return np.concatenate([np.linspace(a,b,max(2,int(np.linalg.norm(b-a)/.2)+1)) for a,b in zip(points,points[1:])])
routes=[sample(perimeter_path(n,r),r) for n,r in ((10,4.),(22,5.5))]
bank_gap=cKDTree(routes[0]).query(routes[1])[0].min()-4-5.5-.4
assert bank_gap>1.,bank_gap
gaps=[];old_gaps=[]
for sx in (-1,1):
    for k,(dx,r) in enumerate(((8,7.),(26,9.),(44,6.))):
        e=sx*(1000-dx-4);n=220+k*22
        riser=np.array([[e,n,z] for z in np.arange(40,990.1,.2)])
        for i,(n_off,rp) in enumerate(((10,4.),(22,5.5))):
            gaps.append(cKDTree(riser).query(routes[i])[0].min()-r-rp-.4)
            old_gaps.append(abs(sx*(1000-n_off)-e)-r-rp-.4)
assert min(gaps)>2.,gaps
report={'nativeLod0Triangles':sum(faces.values()),'nativeMaterialTriangles':dict(faces),'approvedVertexErrorInches':float(error),
        'incorrectWindingTriangles':bad_winding,'finiteGeometryUVsNormals':True,'minimumJacketClearanceBetweenPipesInches':round(float(bank_gap),3),
        'minimumJacketClearanceToRisersInches':round(float(min(gaps)),3),'previousWorstRiserClearanceInches':round(min(old_gaps),3),
        'nativeEngineValidation':False}
(OUT/'stage-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
