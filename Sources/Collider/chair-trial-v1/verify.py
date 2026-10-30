"""Validate review meshes, unchanged original map sources and collision."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/chair'
ASSET=ROOT/'Assets/models/props/collider/chair-trial-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accepted_path=ROOT/'output/collider-chair-accepted-20261029/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(manifest['protectedSourceSHA256'])
if accepted:
    for record in accepted['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
for path,h in guards.items():assert sha(ROOT/path)==h,path
reports={};physics=[]
for name in ('before','after'):
    directory=ROOT/'output/collider-chair-accepted-20261029/retired-before-resources' if accepted and name=='before' else ASSET
    p=directory/(name+'.obj');assert sha(p)==manifest['models'][name]['meshSHA256']
    vertices=[];uv=[];normals=[];areas=[];bad=0;paint='';materials=set();fabric_ratios=[]
    for line in p.read_text().splitlines():
        if line.startswith('v '):vertices.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):normals.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('usemtl '):paint=line[7:];materials.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            assert len(ids)==3
            points=np.array([vertices[v] for v,t,n in ids]);cross=np.cross(points[1]-points[0],points[2]-points[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate');areas.append(area)
            if name=='after' and paint=='op_fabric':
                tex=np.array([uv[t] for v,t,n in ids]);a,b=tex[1]-tex[0],tex[2]-tex[0]
                ratio=abs(a[0]*b[1]-a[1]*b[0])*.5*36./area
                assert ratio>.25,('Collapsed or stretched fabric UV',ratio)
                fabric_ratios.append(ratio)
            if np.dot(cross,np.mean([normals[n] for v,t,n in ids],axis=0))<-1e-7:bad+=1
            for v,t,n in ids:assert np.isfinite(np.concatenate((vertices[v],uv[t],normals[n]))).all()
    assert bad==0,(name,'windingErrors',bad)
    assert len(areas)==manifest['models'][name]['triangles']
    doc=(directory/(name+'.vmdl')).read_bytes();marker=b'PhysicsShapeList';physics.append(doc[doc.index(marker):])
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc.decode()))
    for paint in materials:
        mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
        for tex in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
            if tex.startswith('[') or tex.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/tex).is_file(),tex
    reports[name]={'triangles':len(areas),'windingErrors':bad,'degenerateTriangles':0,
        'finiteUVsAndNormals':True,'minimumTriangleArea':min(areas),'validMaterialSources':len(materials),'meshSHA256':sha(p)}
    if fabric_ratios:reports[name]['minimumFabricUVPhysicalAreaRatio']=min(fabric_ratios)
assert physics[0]==physics[1]
result={'candidateInstalledInMap':bool(accepted),'acceptedCaseCabinetMonitorAndMapSourcesPreserved':True,
    'identicalOriginalCollisionBytes':True,'variants':reports,'editorUsed':False,'engineCompilation':'pending'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
