"""Verify the installed camera delta against the retained pre-install sources."""
from collections import Counter
from pathlib import Path
import sys, json, ast, hashlib
import native
sys.path.insert(0,str(native.ROOT/'Tools'))
import riverdale_splice as splice

report=[]
manifest=json.loads((native.OUT/'manifest.json').read_text())
for entry in manifest['models']:
    name=entry['name']
    relative=Path('Assets/models/maps/riverdale')/f'{name}.obj'
    original=Counter(splice.read_obj(native.OUT/'retired'/relative)[1])
    installed=Counter(splice.read_obj(native.ROOT/relative)[1])
    old=Counter(splice.read_obj(native.OUT/'stage'/f'{name}-old.obj')[1])
    new=Counter(splice.read_obj(native.OUT/'stage'/f'{name}-new.obj')[1]) if entry['new_camera_triangles'] else Counter()
    assert installed==original-old+new, name
    assert not old&installed, f'Old camera faces remain: {name}'
    assert installed-new==original-old, f'Non-camera geometry changed: {name}'
    vmdl=(native.ROOT/relative.with_suffix('.vmdl')).read_text()
    assert 'cctv_v2_review' not in vmdl
    if new:
        for paint in {m for m,_ in new}:
            assert f'materials/riverdale/cctv_v2/{paint}.vmat' in vmdl
    report.append(dict(Model=name,OldCameraFacesRemoved=sum(old.values()),NewCameraFaces=sum(new.values()),
                       OtherFacesPreserved=True,InstalledSha256=hashlib.sha256((native.ROOT/relative).read_bytes()).hexdigest()))
for name in ('riverdale_hall','riverdale_map','riverdale_camera'):
    ast.parse((native.ROOT/'Tools'/f'{name}.py').read_text())
(native.OUT/'installed-source-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
for suffix in ('detail','fine'):
    path=f'models/maps/riverdale/riverdale_hall_{suffix}.vmdl'
    result=native.call('asset_compile',dict(path=path,full=False))
    assert result.get('Success'),result
    print(json.dumps(result),flush=True)
