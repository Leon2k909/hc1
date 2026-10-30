"""Check actual valve geometry, wheel unwrap, dependencies and protected sources."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261029/valve'
ASSET=ROOT/'Assets/models/props/collider/valve-trial-v1'
manifest=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accepted_path=ROOT/'output/collider-valve-accepted-20261029/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(manifest['protectedSourceSHA256'])
if accepted:
    for record in accepted['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
for path,h in guards.items():assert sha(ROOT/path)==h,path
reports={}
for name in ('before','after'):
    directory=ROOT/'output/collider-valve-accepted-20261029/retired-before-resources' if accepted and name=='before' else ASSET
    path=directory/(name+'.obj');assert sha(path)==manifest['models'][name]['meshSHA256']
    vs=[];uv=[];ns=[];paint='';materials=set();areas=[];bad=0;wheel_area=0.;wheel_triangles=0;bore_triangles=0
    for line in path.read_text().splitlines():
        if line.startswith('v '):vs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):ns.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('usemtl '):paint=line[7:];materials.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]];assert len(ids)==3
            points=np.array([vs[v] for v,t,n in ids]);cross=np.cross(points[1]-points[0],points[2]-points[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate');areas.append(area)
            if np.dot(cross,np.mean([ns[n] for v,t,n in ids],axis=0))<-1e-7:bad+=1
            for v,t,n in ids:assert np.isfinite(np.concatenate((vs[v],uv[t],ns[n]))).all()
            if name=='after' and paint=='vv_bore' and np.ptp(points[:,0])>23.:
                radial=np.column_stack((np.zeros(3),points[:,1]-13.,points[:,2]))
                if np.all(abs(np.linalg.norm(radial,axis=1)-5.)<.01):
                    assert all(np.dot(radial[i],ns[n])<-4.8 for i,(v,t,n) in enumerate(ids))
                    bore_triangles+=1
            if paint=='vv_wheel':
                tex=np.array([uv[t] for v,t,n in ids]);assert tex.min()>=0 and tex.max()<=1
                a,b=tex[1]-tex[0],tex[2]-tex[0];a=abs(a[0]*b[1]-a[1]*b[0])*.5
                assert a>1e-7;wheel_area+=a;wheel_triangles+=1
    assert bad==0,(name,'windingErrors',bad)
    assert len(areas)==manifest['models'][name]['triangles']
    doc=(directory/(name+'.vmdl')).read_text();assert 'PhysicsShapeList' not in doc
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    for paint in materials:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for tex in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
            if tex.startswith('[') or tex.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/tex).is_file(),tex
    reports[name]={'triangles':len(areas),'windingErrors':bad,'degenerateTriangles':0,'finiteUVsAndNormals':True,
        'minimumTriangleArea':min(areas),'validMaterialSources':len(materials),'authoredCollisionShapes':0,'meshSHA256':sha(path)}
    if name=='after':
        assert wheel_triangles==2048 and abs(wheel_area-1)<1e-6
        assert bore_triangles==96,'Port bore interior missing or facing out'
        reports[name].update(wheelUVUnwrapArea=wheel_area,wheelUVTriangles=wheel_triangles,inwardBoreTriangles=bore_triangles)
result={'candidateInstalledInMap':bool(accepted),'allAcceptedUpgradesAndMapSourcesPreserved':True,'variants':reports,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
