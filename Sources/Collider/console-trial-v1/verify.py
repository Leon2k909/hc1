"""Scope, topology, actual-baseline and dependency checks without an engine process."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[name]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261030/console'
ASSET=ROOT/'Assets/models/props/collider/console-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
accepted_path=ROOT/'output/collider-console-accepted-20261030/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(manifest['protectedSourceSHA256'])
if accepted:
    for record in accepted['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
for path,h in guards.items():assert sha(ROOT/path)==h,path
reports={}
for name in ('before','after'):
    directory=ROOT/'output/collider-console-accepted-20261030/retired-before-resources' if accepted and name=='before' else ASSET
    path=directory/(name+'.obj');assert sha(path)==manifest['models'][name]['meshSHA256']
    vs=[];uv=[];ns=[];paint='';paints=set();areas=[];bad=[];screen_uv=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):vs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):ns.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('usemtl '):paint=line[7:];paints.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]];assert len(ids)==3
            pts=np.array([vs[v] for v,t,n in ids]);cross=np.cross(pts[1]-pts[0],pts[2]-pts[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate',pts.tolist());areas.append(float(area))
            if cross@np.mean([ns[n] for v,t,n in ids],axis=0)<-1e-7:bad.append(paint)
            for v,t,n in ids:
                assert np.isfinite(np.concatenate((vs[v],uv[t],ns[n]))).all()
                assert abs(np.linalg.norm(ns[n])-1)<1e-3,(name,paint,n,ns[n].tolist(),float(np.linalg.norm(ns[n])))
            if paint=='co_screens':screen_uv.extend(uv[t] for v,t,n in ids)
    assert not bad,(name,'windingErrors',len(bad),dict((k,bad.count(k)) for k in set(bad)))
    assert len(areas)==manifest['models'][name]['triangles']
    doc=(directory/(name+'.vmdl')).read_text()
    assert doc.count('_class = "PhysicsShapeBox"')==1
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    dependencies=set()
    for paint in paints:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for tex in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
            if tex.startswith('[') or tex.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/tex).is_file(),tex;dependencies.add(tex)
    uvscreen=np.array(screen_uv)
    assert np.allclose(uvscreen.min(axis=0),(.5,.5)) and np.allclose(uvscreen.max(axis=0),(1.,1.))
    reports[name]={'triangles':len(areas),'windingErrors':0,'degenerateTriangles':0,
        'finiteUVsAndUnitNormals':True,'validMaterials':len(paints),'textureSources':len(dependencies),
        'minimumTriangleArea':min(areas),'screenAtlasUVBounds':[uvscreen.min(axis=0).tolist(),uvscreen.max(axis=0).tolist()],
        'meshSHA256':sha(path),'objBounds':[np.min(vs,axis=0).tolist(),np.max(vs,axis=0).tolist()]}
def physics(name):
    directory=ROOT/'output/collider-console-accepted-20261030/retired-before-resources' if accepted and name=='before' else ASSET
    s=(directory/(name+'.vmdl')).read_text();return s[s.index('_class = "PhysicsShapeList"'):]
assert physics('before')==physics('after')
assert manifest['baseline']['exactMatchedTriangles']==reports['before']['triangles']
result={'candidateInstalledInMap':bool(accepted),'originalAssetRetainedOutsideAssets':bool(accepted),
    'protectedSourcesUnchanged':len(manifest['protectedSourceSHA256']),
    'previousAcceptedModelsAndMaterialsPreserved':True,'collisionUnchanged':True,
    'variants':reports,'editorUsed':False,'engineCompilation':'pending','nativeAppearanceAndPerformance':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
