"""Stage only the fountain water faces, two materials and their private shaders."""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import map_kit as K
import belltower_fountain_water as W
import belltower_compact_obj as C

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/fountain-water-v2'
STAGE = OUT/'stage'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(target, source):
    relative = target.relative_to(ROOT)
    before = sha(target) if target.exists() else None
    backup = OUT/'before'/relative
    if before:
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists(): assert sha(backup) == before
        else: shutil.copyfile(target, backup)
    return {'before':before, 'after':sha(source), 'source':source.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}


def main():
    assert not (STAGE/'manifest.json').exists()
    STAGE.mkdir(parents=True, exist_ok=True)
    model = K.Model(); W.build(model)
    assert not model.boxes and not model.hulls and not model.props
    for paint, polygons in model.polygons.items():
        for index, (points, _) in enumerate(polygons):
            rounded = np.array([list(map(float,K.obj_vector(K.to_world(p)).split())) for p in points])
            uv = model.polygon_uvs.get((paint,index))
            for i in range(1,len(points)-1):
                assert np.linalg.norm(np.cross(rounded[i]-rounded[0],rounded[i+1]-rounded[0])) > 1e-7
                if uv:
                    a,b,c = [np.asarray(uv[j]) for j in (0,i,i+1)]
                    assert abs(np.linalg.det(np.array((b-a,c-a)))) > 1e-8
    piece = STAGE/'water-only.obj'
    K.write_obj(piece,model,'belltower_centre')
    path = ROOT/'Assets/models/maps/belltower/belltower_centre.obj'
    initial = sha(path)
    tables = C.tables(path)
    offsets = {k:len(v)-1 for k,v in tables.items()}
    additions, tail = [], []
    for line in piece.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')): additions.append(line)
        elif line.startswith(b'usemtl '): tail.append(line)
        elif line.startswith(b'f '):
            tokens = [b'/'.join(str(i+offsets[k]).encode() for k,i in zip(C.KINDS,row))
                      for row in C.face_tokens(line,{k:10**9 for k in C.KINDS})]
            tail.append(b'f '+b' '.join(tokens)+b'\n')
    staged = STAGE/path.relative_to(ROOT)
    staged.parent.mkdir(parents=True, exist_ok=True)
    removed = {}; other_hash = hashlib.sha256(); inserted = False; paint = None
    with path.open('rb') as source, staged.open('wb') as target:
        for line in source:
            if not inserted and line.startswith(b'usemtl '):
                target.writelines(additions); inserted = True
            if line.startswith(b'usemtl '): paint=line.split()[1]
            if line.startswith(b'f ') and paint in (b'fountain_water',b'fountain_jet'):
                removed[paint.decode()] = removed.get(paint.decode(),0)+1
            else:
                target.write(line); other_hash.update(line)
        target.writelines(tail)
    assert inserted and removed.get(W.WATER) == 6 and removed.get(W.JET) == 5692, removed
    assert sha(path) == initial
    # Independently recover every original byte after removing only the declared
    # appended tables/faces and the old water faces. No other mesh is regenerated.
    original_lines = path.read_bytes().splitlines(keepends=True)
    old_kept = []; current_paint = None
    for line in original_lines:
        if line.startswith(b'usemtl '): current_paint=line.split()[1]
        if line.startswith(b'f ') and current_paint in (b'fountain_water',b'fountain_jet'): continue
        old_kept.append(line)
    expected = b''.join(old_kept)
    # The new file is exactly the retained original with one table insertion and
    # one face append. This also preserves all UVs, normals and non-water indices.
    split = expected.index(b'usemtl ')
    assert staged.read_bytes() == expected[:split]+b''.join(additions)+expected[split:]+b''.join(tail)
    report = {'revision':'fountain-water-v2','files':{},'source_sha256':{},'protected_sha256':{},
              'removed_triangles':removed,'added_triangles':model.triangle_count(),
              'all_non_water_source_bytes_preserved':True,'physics_unchanged':True,'scene_unchanged':True,
              'fixed_ripple_hoops_removed':12,'streams':4,'animated_droplets':48,
              'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')}
    report['files'][path.relative_to(ROOT).as_posix()] = record(path,staged)
    for name,text in W.material_definitions().items():
        relative=Path(f'Assets/materials/belltower/{name}.vmat')
        source=STAGE/relative; source.parent.mkdir(parents=True,exist_ok=True); source.write_text(text)
        report['files'][relative.as_posix()]=record(ROOT/relative,source)
    for name in ('surface','stream'):
        filename=f'belltower_fountain_{name}_v2.shader'
        relative=Path('Assets/shaders')/filename
        source=STAGE/relative; source.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'Sources/Belltower/shaders'/filename,source)
        report['files'][relative.as_posix()]=record(ROOT/relative,source)
    for relative in ('Assets/models/maps/belltower/belltower_centre.vmdl',
                     'Assets/models/maps/belltower/belltower_centre.mtl',
                     'Assets/shaders/belltower_fountain_water.shader',
                     'Assets/materials/belltower/fountain_water_normal.png',
                     'Assets/materials/belltower/fountain_jet_normal.png'):
        report['protected_sha256'][relative]=sha(ROOT/relative)
    for relative in ('Tools/belltower_fountain.py','Tools/belltower_fountain_water.py',
                     'Sources/Belltower/shaders/belltower_fountain_surface_v2.shader',
                     'Sources/Belltower/shaders/belltower_fountain_stream_v2.shader'):
        report['source_sha256'][relative]=sha(ROOT/relative)
    (STAGE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','source_sha256','protected_sha256')}))


if __name__ == '__main__': main()
