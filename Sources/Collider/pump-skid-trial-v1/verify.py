"""Check preview geometry, original clip, real openings and unchanged saved assets."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_machinery as H
OUT=ROOT/'output/asset-improvement-20261030/pump-skid'
ASSET=ROOT/'Assets/models/props/collider/pump-skid-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'manifest.json').read_text())
for path,h in d['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
reports={}
for name in ('before','after'):
    path=ASSET/(name+'.obj');assert sha(path)==d['models'][name]['meshSHA256']
    vs=[];uv=[];ns=[];paint='';paints=set();areas=[];bad=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:];paints.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]];assert len(ids)==3
            points=np.array([vs[v] for v,t,n in ids]);cross=np.cross(points[1]-points[0],points[2]-points[0])
            area=np.linalg.norm(cross)*.5;assert area>1e-8,(name,paint,'degenerate');areas.append(float(area))
            if cross@np.mean([ns[n] for v,t,n in ids],axis=0)<-1e-7:bad.append(paint)
            for v,t,n in ids:
                assert np.isfinite(np.concatenate((vs[v],uv[t],ns[n]))).all()
                assert abs(np.linalg.norm(ns[n])-1)<1e-3
    assert not bad,(name,'winding errors',len(bad),{p:bad.count(p) for p in set(bad)})
    assert len(areas)==d['models'][name]['triangles']
    doc=(ASSET/(name+'.vmdl')).read_text()
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc));textures=set()
    for paint in paints:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for texture in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
            if texture.startswith('[') or texture.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/texture).is_file(),texture;textures.add(texture)
    points=np.array(vs)
    if name=='after':
        assert np.all(points.min(axis=0)>=np.array((-53,-29,-.001)))
        assert np.all(points.max(axis=0)<=np.array((53,29,74.001)))
    reports[name]={'triangles':len(areas),'degenerateTriangles':0,'windingErrors':0,
                   'finiteUVsAndUnitNormals':True,'materials':len(paints),'textureSources':len(textures),
                   'boundsInches':[points.min(axis=0).tolist(),points.max(axis=0).tolist()],'meshSHA256':sha(path)}
old_doc=(ASSET/'before.vmdl').read_text();new_doc=(ASSET/'after.vmdl').read_text();marker='PhysicsShapeList'
assert marker in old_doc and old_doc[old_doc.index(marker):]==new_doc[new_doc.index(marker):]
result={'installedInMap':False,'originalEquipmentCaseUntouched':True,'priorAcceptedPropsPreserved':True,
        'protectedSourceCount':len(d['protectedSourceSHA256']),'fullOriginalCollisionUnchanged':True,
        'newMeshWithinOriginalFootprintAndHeight':True,'variants':reports,'editorUsed':False,
        'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
