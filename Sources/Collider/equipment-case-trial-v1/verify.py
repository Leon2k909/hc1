"""Validate the review meshes, matching physics and untouched original assets."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/equipment-case'
ASSET=ROOT/'Assets/models/props/collider/equipment-case-trial-v1'
manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accepted_path=ROOT/'output/collider-case-accepted-20261029/installed.json'
accepted=json.loads(accepted_path.read_text()) if accepted_path.exists() else None
current_guards=dict(manifest['originalAssetsSHA256'])
if accepted:
    current_guards.update({'Assets/'+r['relative']:r['after'] for r in accepted['files']})
cabinet_path=ROOT/'output/collider-cabinet-accepted-20261029/installed.json'
if cabinet_path.exists():
    cabinet=json.loads(cabinet_path.read_text());path='Assets/'+cabinet['relative']
    assert current_guards[path]==cabinet['beforeSHA256'],'Cabinet must follow the accepted case'
    current_guards[path]=cabinet['afterSHA256']
for path,expected in current_guards.items():
    assert sha(ROOT/path)==expected, ('Original changed',path)
reports={}
physics=[]
for name in ('before','after'):
    directory=ROOT/'output/collider-case-accepted-20261029/retired-before-resources' if accepted and name=='before' else ASSET
    path=directory/(name+'.obj')
    vertices=[];normals=[];uvs=[];areas=[];bad=0;paint='';materials=set()
    for line in path.read_text().splitlines():
        if line.startswith('v '):vertices.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):normals.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vt '):uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('usemtl '):paint=line[7:];materials.add(paint)
        elif line.startswith('f '):
            indices=[[int(v)-1 for v in word.split('/')] for word in line.split()[1:]]
            assert len(indices)==3
            points=np.array([vertices[v] for v,t,n in indices])
            cross=np.cross(points[1]-points[0],points[2]-points[0])
            area=np.linalg.norm(cross)*.5
            assert area>1e-8,(name,paint,'degenerate')
            areas.append(area)
            mean=np.mean([normals[n] for v,t,n in indices],axis=0)
            if np.dot(cross,mean)<-1e-7:bad+=1
            for v,t,n in indices:assert np.isfinite(np.concatenate((vertices[v],uvs[t],normals[n]))).all()
    doc=(directory/(name+'.vmdl')).read_text()
    marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
    physics.append(doc[doc.index(marker):])
    remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    for paint in materials:
        material=ROOT/'Assets'/remaps[paint+'.vmat']
        assert material.is_file(),material
        text=material.read_text()
        for texture in re.findall(r'Texture\w+\s+"([^"]+)"',text):
            if texture.startswith('[') or texture.startswith('materials/default/'):continue
            assert (ROOT/'Assets'/texture).is_file(),texture
    reports[name]={'triangles':len(areas),'windingErrors':bad,'minimumTriangleArea':min(areas),
        'finiteUVsAndNormals':True,'validSourceMaterials':len(materials),'meshSHA256':sha(path)}
assert reports['after']['windingErrors']==0,reports['after']
assert physics[0]==physics[1], 'The review variants must retain identical collision'
result={'originalAssetsUnchanged':not bool(accepted),'approvedMapReplacementVerified':bool(accepted),
    'identicalAuthoredCollision':True,'variants':reports,'engineCompiled':False,'usedBySavedMap':bool(accepted)}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
