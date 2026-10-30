"""Read-only verification of the published Veridant chair geometry and bindings."""
import hashlib
import json
from pathlib import Path
import re

import numpy as np

from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/chair-v4'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    manifest=json.loads((OUT/'stage-v4/manifest.json').read_text())
    assert all(sha(ROOT/p)==row['after'] for p,row in manifest['files'].items())
    document=(ROOT/'Assets/models/maps/veridant/veridant_dress.vmdl').read_text()
    before=(OUT/'stage-v2/before/Assets/models/maps/veridant/veridant_dress.vmdl').read_text()
    a,b=span(document,'_class = "PhysicsShapeList"'); c,d=span(before,'_class = "PhysicsShapeList"')
    assert document[a:]==before[c:],'Physics changed'
    counts=[]; sampled=0; collapsed=0
    for index in range(2):
        relative=f'models/maps/veridant/chair-v4/chairs-{index}.obj'
        assert document.count(relative)==1
        positions=[None]; texcoords=[None]; normals=[None]; count=0; paint=None
        for line in (ROOT/'Assets'/relative).open():
            tokens=line.split()
            if not tokens: continue
            if tokens[0] in ('v','vt','vn'):
                target={'v':positions,'vt':texcoords,'vn':normals}[tokens[0]]
                values=np.array([float(v) for v in tokens[1:]])
                assert np.isfinite(values).all(); target.append(values)
            elif tokens[0]=='usemtl': paint=tokens[1]
            elif tokens[0]=='f':
                ids=np.array([[int(v) for v in token.split('/')] for token in tokens[1:]])
                assert len(ids)==3
                p=np.array([positions[i] for i in ids[:,0]])
                assert np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-9,(relative,paint,p.tolist(),ids.tolist())
                if paint=='vr_chair_walnut' and len(set(ids[:,2]))>1:
                    uv=np.array([texcoords[i] for i in ids[:,1]])
                    delta=uv[1:]-uv[0]
                    collapsed+=abs(np.linalg.det(delta))<1e-10
                    sampled+=1
                count+=1
        assert max(len(positions),len(texcoords),len(normals))<=65536
        counts.append(count)
    assert collapsed==0 and sampled>2000,'Timber side faces need usable grain UVs'
    assert sum(counts)==sum(manifest['triangles_per_chair'])
    for name in ('cloth','piping','walnut'):
        assert document.count(f'from = "vr_chair_{name}.vmat"')==1
        assert f'materials/veridant/chair-v4/{name}.vmat' in document
    import veridant_map as V
    import veridant_chair_soft as C
    import map_kit as K
    model=K.Model()
    for name,path in C.MATERIALS.items():
        if name.startswith('vr_chair_'):
            model.polygons[name]=[];model.material_overrides[name]=path
    V.configure(model)
    assert all(model.material_overrides[name]==path for name,path in C.MATERIALS.items() if name.startswith('vr_chair_'))
    installed=json.loads((OUT/'installed.json').read_text())
    assert installed['TrianglesPerChair']==manifest['triangles_per_chair'],'Await the final native compile receipt'
    assert not installed['ModelIsError']
    assert all(row['IsCompiled'] and row['IsCompiledAndUpToDate'] and not row['IsCompileFailed'] for row in installed['Compiled'])
    result={'instances':manifest['instances'],'triangles':sum(counts),
            'triangles_per_chair':manifest['triangles_per_chair'],
            'published_files_match':True,'physics_suffix_unchanged':True,
            'timber_side_triangles_with_valid_uvs':sampled,'collapsed_timber_side_uvs':int(collapsed),
            'future_generator_material_bindings_preserved':True,
            'native_resources_compiled':len(installed['Compiled']),
            'views':[str(OUT/'final'/f'{name}.png') for name in ('chair','front','rear','terrace')]}
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
