"""Validate actual exported monitor geometry and unchanged accepted map sources."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/monitor'
ASSET=ROOT/'Assets/models/props/collider/monitor-trial-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accepted_path=ROOT/'output/collider-monitor-accepted-20261029/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
guards=dict(manifest['protectedSourceSHA256'])
if accepted:
    for record in accepted['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
chair_path=ROOT/'output/collider-chair-accepted-20261029/installed.json'
if chair_path.exists():
    for record in json.loads(chair_path.read_text())['files']:
        path='Assets/'+record['relative'];assert guards[path]==record['before'];guards[path]=record['after']
for path,expected in guards.items():
    assert sha(ROOT/path)==expected,('Protected source changed',path)
reports={}
for name in ('before','after'):
    directory=ROOT/'output/collider-monitor-accepted-20261029/retired-before-resources' if accepted and name=='before' else ASSET
    path=directory/(name+'.obj')
    assert sha(path)==manifest['models'][name]['meshSHA256']
    vertices=[];uvs=[];normals=[];areas=[];bad=0;paint='';materials=set();screen=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:];materials.add(paint)
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            assert len(ids)==3
            points=np.array([vertices[v] for v,t,n in ids])
            cross=np.cross(points[1]-points[0],points[2]-points[0]);area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate');areas.append(area)
            if np.dot(cross,np.mean([normals[n] for v,t,n in ids],axis=0))<-1e-7:bad+=1
            for v,t,n in ids:
                assert np.isfinite(np.concatenate((vertices[v],uvs[t],normals[n]))).all()
                if paint=='co_screens':screen.append((vertices[v],uvs[t]))
    assert bad==0,(name,'winding',bad)
    assert len(areas)==manifest['models'][name]['triangles']
    doc=(directory/(name+'.vmdl')).read_text()
    assert 'PhysicsShapeList' not in doc,'Original monitor has no authored collision'
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    for paint in materials:
        material=ROOT/'Assets'/remaps[paint+'.vmat']
        assert material.is_file(),material
        for texture in re.findall(r'Texture\w+\s+"([^"]+)"',material.read_text()):
            if texture.startswith('[') or texture.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/texture).is_file(),texture
    assert remaps['co_screens.vmat']=='materials/collider/co_screens.vmat'
    for point,uv in screen:
        expected=np.array(((point[0]+56.)/112.*.5,.5+(point[2]-2.5)/66.*.5))
        assert np.allclose(uv,expected,atol=1e-5,rtol=0),(name,point,uv,expected)
        assert -1e-5<=uv[0]<=.50001 and .49999<=uv[1]<=1.00001
    reports[name]={'triangles':len(areas),'windingErrors':bad,'degenerateTriangles':0,
        'minimumTriangleArea':min(areas),'finiteUVsAndNormals':True,'sourceMaterialsResolved':len(materials),
        'existingAtlasAndActiveImageScalePreserved':True,'authoredCollisionShapes':0,'meshSHA256':sha(path)}
assert reports['before']['triangles']==26
result={'acceptedCaseCabinetAndMapSourcesUnchanged':True,'exactSavedBaselineTriangles':26,
    'candidateInstalledInMap':bool(accepted),'editorUsed':False,'engineCompilation':'pending','variants':reports}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
