"""Verify the isolated cooling unit, original scope and material dependencies."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import hashlib,json,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'
ASSET=ROOT/'Assets/models/props/collider/cooling-unit-trial-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
accepted_path=ROOT/'output/collider-cooling-unit-accepted-20261030/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(manifest['protectedSourceSHA256'])
if accepted:
    for record in accepted['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
for path,h in guards.items():assert sha(ROOT/path)==h,path
reports={}
for name in ('before','after'):
    directory=ROOT/'output/collider-cooling-unit-accepted-20261030/retired-before-resources' if accepted and name=='before' else ASSET
    path=directory/(name+'.obj');assert sha(path)==manifest['models'][name]['meshSHA256']
    vs=[];uv=[];ns=[];paint='';paints=set();areas=[];bad=[];display=[];fan_faces=0;blade_edges=Counter();blade_volume=0.
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
                assert abs(np.linalg.norm(ns[n])-1)<1e-3
            if paint=='co_screens':display.extend(uv[t] for v,t,n in ids)
            if paint=='cu_blade':
                fan_faces+=1;blade_volume+=float(pts[0]@np.cross(pts[1],pts[2]))/6
                vertices=[tuple(p) for p in pts]
                for i in range(3):blade_edges[(vertices[i],vertices[(i+1)%3])]+=1
    assert not bad,(name,'winding',dict(Counter(bad)))
    if name=='after':
        assert blade_edges and all(n==1 and blade_edges[(b,a)]==1 for (a,b),n in blade_edges.items()),'Blade boundary gap or inconsistent winding'
        assert blade_volume>0,('Inward blade shells',blade_volume)
    assert len(areas)==manifest['models'][name]['triangles']
    doc=(directory/(name+'.vmdl')).read_text();assert 'PhysicsShapeList' not in doc
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc));textures=set()
    for paint in paints:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for tex in re.findall(r'Texture\w+\s+"([^\"]+)"',mat.read_text()):
            if tex.startswith('[') or tex.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/tex).is_file(),tex;textures.add(tex)
    display=np.array(display);assert np.allclose(display.min(axis=0),(0,0)) and np.allclose(display.max(axis=0),(.5,.5))
    reports[name]={'triangles':len(areas),'windingErrors':0,'degenerateTriangles':0,'finiteUVsAndUnitNormals':True,
        'materials':len(paints),'textureSources':len(textures),'collisionShapes':0,
        'minimumTriangleArea':min(areas),'screenAtlasUVBounds':[display.min(axis=0).tolist(),display.max(axis=0).tolist()],
        'fanBladeTriangles':fan_faces,'meshSHA256':sha(path)}
    if name=='after':reports[name].update(closedOrientedFanBladeShells=True,bladeVolumeCubicInches=blade_volume)
assert reports['before']['triangles']==170 and reports['after']['fanBladeTriangles']>3500
result={'candidateInstalledInMap':bool(accepted),'oldAssetRollbackOutsideAssets':bool(accepted),'allAcceptedUpgradesPreserved':True,
    'protectedSourceCount':len(manifest['protectedSourceSHA256']),'variants':reports,
    'editorUsed':False,'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
