"""Verify published chair sources, preserved map imports, and native receipts."""
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import veridant_chair_authored as C
from belltower_safe_imports import span

OUT=ROOT/'output/veridant/chair-v5'
stage=(OUT/'publish-stage.txt').read_text().strip()
manifest=json.loads((OUT/stage/'manifest.json').read_text())
for relative,row in manifest['files'].items():
    with (ROOT/relative).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==row['after'],relative

relative=Path('Assets/models/maps/veridant/veridant_dress.vmdl')
before=(OUT/'stage-v1/before'/relative).read_bytes().decode('utf-8')
after=(ROOT/relative).read_bytes().decode('utf-8')
a,b=span(before,'_class = "PhysicsShapeList"');c,d=span(after,'_class = "PhysicsShapeList"')
assert before[a:]==after[c:]
def imports(text):
    a,b=span(text,'_class = "RenderMeshList"')
    return re.findall(r'filename\s*=\s*"([^"]+)"',text[a:b])
original=imports(before);current=imports(after)
assert [p for p in original if '/chair-v4/' not in p]==[p for p in current if '/chair-v5/' not in p]
assert len([p for p in current if '/chair-v5/' in p])==4
assert after.count('from = "vr_chair_authored.vmat"')==1
mesh=C.mesh();count=len(mesh['positions']);counts=[];floor_errors=[]
for index in range(4):
    path=ROOT/f'Assets/models/maps/veridant/chair-v5/chairs-{index}.obj'
    positions=[];normals=[];uv=[];face_count=0
    for line in path.open():
        if line.startswith('v '):positions.append([float(v) for v in line.split()[1:]])
        elif line.startswith('vn '):normals.append([float(v) for v in line.split()[1:]])
        elif line.startswith('vt '):uv.append([float(v) for v in line.split()[1:]])
        elif line.startswith('f '):face_count+=1
    assert len(positions)==len(normals)==len(uv)==count*3<65536
    positions=np.array(positions);normals=np.array(normals);uv=np.array(uv)
    assert np.isfinite(positions).all() and np.isfinite(normals).all() and np.isfinite(uv).all()
    for j,row in enumerate(manifest['placements'][index*3:index*3+3]):
        expected,n,tex,faces=C.transform(row['at'],row['facing'],row['z0'])
        expected=np.column_stack((-expected[:,0],expected[:,2],expected[:,1]))
        n=np.column_stack((-n[:,0],n[:,2],n[:,1]))
        part=slice(j*count,(j+1)*count)
        assert np.allclose(positions[part],expected,atol=6e-7,rtol=0)
        assert np.allclose(normals[part],n,atol=6e-8,rtol=0)
        assert np.allclose(uv[part],tex,atol=6e-8,rtol=0)
        floor_errors.append(abs(float(positions[part,1].min())-row['z0']))
    counts.append(face_count)
assert sum(counts)==manifest['total_triangles']
assert max(floor_errors)<.0001
installed=json.loads((OUT/'installed.json').read_text())
assert installed['Stage']==stage
assert not installed['ModelIsError'] and installed['AuthoredMaterialPresent']
assert all(row['IsCompiled'] and row['IsCompiledAndUpToDate'] and not row['IsCompileFailed'] for row in installed['Compiled'])
assert all(installed[name] for name in ('SourceSceneUnchanged','UnsavedStateUnchanged','PlayStateUnchanged'))
capture=json.loads((OUT/'native-after/run_csharp.json').read_text())
capture=next(json.loads(item['text']) for item in capture['content'] if item['type']=='text')
assert capture['Stage']==stage
assert all(capture[name] for name in ('SourceSceneUnchanged','UnsavedStateUnchanged','PlayStateUnchanged'))
assert not capture['ModelIsError']
report={'stage':stage,'installed':True,'instances':manifest['instances'],
        'triangles_per_chair':manifest['triangles_per_chair'],'total_triangles':sum(counts),
        'published_files_match':True,'physics_suffix_unchanged':True,'other_render_imports_unchanged':True,
        'maximum_floor_error_inches':max(floor_errors),
        'authored_positions_normals_uv_preserved':True,'native_resources_compiled':len(installed['Compiled']),
        'source_scene_unsaved_and_play_state_preserved':True,'native_captures':capture['Files']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
