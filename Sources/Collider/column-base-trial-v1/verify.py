"""Check source scope, hardware geometry, old collision fit and unchanged context."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/column-base'
ASSET=ROOT/'Assets/models/props/collider/column-base-trial-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'manifest.json').read_text())
for path,h in d['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
assert sha(OUT/'context/context.obj')==d['contextMeshSHA256']
assert sum(line.startswith('f ') for line in (OUT/'context/context.obj').read_text().splitlines())==36
anchors=[(x,y) for x in (-29.,29.) for y in (-24.,-8.,8.,24.)]
reports={}
for name in ('before','after'):
    path=ASSET/(name+'.obj');assert sha(path)==d['models'][name]['meshSHA256']
    vs=[];uv=[];ns=[];paint='';paints=set();areas=[];bad=[];bores=0
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:];paints.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]];assert len(ids)==3
            pts=np.array([vs[v] for v,t,n in ids]);cross=np.cross(pts[1]-pts[0],pts[2]-pts[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate',pts.tolist());areas.append(float(area))
            if cross@np.mean([ns[n] for v,t,n in ids],axis=0)<-1e-7:bad.append(paint)
            for v,t,n in ids:
                assert np.isfinite(np.concatenate((vs[v],uv[t],ns[n]))).all()
                assert abs(np.linalg.norm(ns[n])-1)<1e-3
            if paint=='cb_bolt' and abs(np.ptp(pts[:,2])-1.24)<.002 and 8.249<=pts[:,2].min()<=8.251:
                for x,y in anchors:
                    radial=pts-np.array((x,y,0));radial[:,2]=0
                    if np.all(abs(np.linalg.norm(radial,axis=1)-.77)<.002):
                        assert all(radial[i]@ns[n]<-.74 for i,(v,t,n) in enumerate(ids));bores+=1
    assert not bad,(name,'winding',len(bad),{k:bad.count(k) for k in set(bad)})
    assert len(areas)==d['models'][name]['triangles']
    doc=(ASSET/(name+'.vmdl')).read_text();assert 'PhysicsShapeList' not in doc
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc));textures=set()
    for paint in paints:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for tex in re.findall(r'Texture\w+\s+"([^\"]+)"',mat.read_text()):
            if tex.startswith('[') or tex.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/tex).is_file(),tex;textures.add(tex)
    points=np.array(vs)
    if name=='after':
        assert points[:,2].min()>=0 and abs(points[:,:2]).max()<=44.001
        upper=points[points[:,2]>8.12];assert abs(upper[:,:2]).max()<=38.001
        assert bores==384,('Hex nut bore triangles',bores)
    reports[name]={'triangles':len(areas),'windingErrors':0,'degenerateTriangles':0,'finiteUVsAndUnitNormals':True,
        'materials':len(paints),'textureSources':len(textures),'collisionShapes':0,'meshSHA256':sha(path),
        'minimumTriangleArea':min(areas),'boundsInches':[points.min(axis=0).tolist(),points.max(axis=0).tolist()]}
    if name=='after':reports[name].update(inwardNutBoreTriangles=bores,withinExistingBaseAndColumnClipEnvelope=True)
assert reports['before']['triangles']==12
result={'candidateInstalledInMap':False,'originalBaseUntouched':True,'allPriorAcceptedUpgradesPreserved':True,
    'actualColumnContextUnchanged':True,'contextTriangles':36,'protectedSourceCount':len(d['protectedSourceSHA256']),
    'variants':reports,'editorUsed':False,'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
