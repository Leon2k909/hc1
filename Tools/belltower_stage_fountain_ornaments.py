"""Stage fountain-only replacement, preserving all unrelated OBJ attributes.

The legacy source snapshot reproduces the exact installed ornaments. Matching
resolved positions removes only those triangles. Centre render imports are
bounded; material remaps and every physics node remain byte-identical.
Nothing is published to Assets by this script.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_fountain_ornaments as O
import belltower_compact_obj as C
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/fountain-ornaments-v2'
LEGACY = ROOT/'Sources/Belltower/props/fountain-ornaments-v2/legacy-source.py.txt'
MAX_FACES = 65000


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def original():
    tree = ast.parse(LEGACY.read_text())
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build')
    fleur = next(n for n in build.body if isinstance(n, ast.FunctionDef) and n.name == 'fleur')
    ellipsoid = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ellipsoid')
    lion_loop = next(n for n in build.body if isinstance(n, ast.For)
                     and any(isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'axes' for t in s.targets) for s in n.body))
    start = next(i for i, s in enumerate(lion_loop.body) if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'axes' for t in s.targets))
    stop = next(i for i, s in enumerate(lion_loop.body) if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                and isinstance(s.value.func, ast.Attribute) and s.value.func.attr == 'spout')
    model = K.Model()
    scope = dict(np=np, math=math, K=K, D=D, model=model, STONE='fountain_limestone',
                 RELIEF='fountain_relief', BRONZE='fountain_bronze', up=np.array((0., 0., 1.)))
    exec(compile(ast.Module(body=[ellipsoid, fleur], type_ignores=[]), str(LEGACY), 'exec'), scope)

    def frame(angle, radius):
        out = np.array((math.cos(angle), math.sin(angle), 0.))
        along = np.array((-out[1], out[0], 0.))
        origin = np.array((0., 130., 0.))+radius*out
        return lambda x, d, z: origin+along*x+out*d+np.array((0., 0., z)), along, out

    for k in range(8):
        scope['fleur'](frame(k*math.pi/4+math.pi/4, 114*math.cos(math.pi/8))[0], 13, .65)
    for k in range(4):
        P, along, out = frame(k*math.pi/2, 27)
        scope.update(P=P, along=along, out=out)
        scope['fleur'](P, 83, 1.25)
        exec(compile(ast.Module(body=lion_loop.body[start:stop], type_ignores=[]), str(LEGACY), 'exec'), scope)
    return model


def point(value):
    return tuple(int(round(float(v)*1000)) for v in value.split())


def keys(model):
    result = Counter()
    for paint, faces in model.polygons.items():
        for points, normal in faces:
            values = [point(K.obj_vector(K.to_world(p))) for p in points]
            for i in range(1, len(values)-1):
                result[(paint.encode(), frozenset((values[0], values[i], values[i+1])))] += 1
    return result


def patch(source, destination, wanted, addition):
    wanted_positions = {p for paint, face in wanted for p in face}
    sparse = {}; offsets = {b'v': 0, b'vt': 0, b'vn': 0}; found = Counter(); removed = set(); paint = None
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            offsets[b'v'] += 1
            p = point(line[2:].decode())
            if p in wanted_positions:
                sparse[offsets[b'v']] = p
        elif line.startswith(b'vt '): offsets[b'vt'] += 1
        elif line.startswith(b'vn '): offsets[b'vn'] += 1
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f ') and paint in (b'fountain_limestone', b'fountain_relief', b'fountain_bronze'):
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = (paint, frozenset(sparse[i] for i in indices))
                if key in wanted:
                    removed.add(number); found[key] += 1
    assert found == wanted, ('Legacy geometry differs', sum((wanted-found).values()), sum((found-wanted).values()))
    tables, faces = [], []
    for line in addition.open('rb'):
        if line.startswith((b'v ', b'vt ', b'vn ')): tables.append(line)
        elif line.startswith(b'usemtl '): faces.append(line)
        elif line.startswith(b'f '):
            tokens = [b'/'.join(str(int(i)+offsets[k]).encode() for k, i in zip(C.KINDS, token.split(b'/')))
                      for token in line.split()[1:]]
            faces.append(b'f '+b' '.join(tokens)+b'\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    kept_before = hashlib.sha256(); kept_after = hashlib.sha256(); inserted = False
    with destination.open('wb') as target:
        for number, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '):
                target.writelines(tables); inserted = True
            if number not in removed:
                kept_before.update(line); target.write(line); kept_after.update(line)
        target.writelines(faces)
    assert inserted and kept_before.digest() == kept_after.digest()
    # Independent reconstruction: exclude added tables/faces and match every old
    # retained byte, including texture coordinates, normals and water triangles.
    raw = destination.read_bytes()
    original_kept = b''.join(line for i, line in enumerate(source.open('rb')) if i not in removed)
    assert raw.replace(b''.join(tables), b'', 1)[:-len(b''.join(faces))] == original_kept
    return {'removed_triangles': len(removed), 'new_triangles': sum(l.startswith(b'f ') for l in faces),
            'unrelated_obj_bytes_sha256': kept_before.hexdigest(), 'unrelated_obj_bytes_exact': True}


def partition(source, vmdl, stage):
    from array import array
    data = C.tables(source)
    counts = {kind: len(values)-1 for kind, values in data.items()}
    parts = []; material = None; current = None
    original_digest = hashlib.sha256()
    for line in source.open('rb'):
        if line.startswith(b'usemtl '): material = line.split()[1].decode(); current = None
        elif line.startswith(b'f '):
            if current is None or len(current['faces'])//9 >= MAX_FACES:
                current = {'material': material, 'faces': array('I')}; parts.append(current)
            face = C.face_tokens(line, counts)
            current['faces'].extend(i for row in face for i in row)
            original_digest.update(material.encode()+b'\n')
            for row in face:
                for kind, index in zip(C.KINDS, row): original_digest.update(data[kind][index])
    text = vmdl.read_text()
    lo, hi = span(text, '_class = "RenderMeshList"')
    old_render = text[lo:hi]
    a, b = span(old_render, '_class = "RenderMeshFile"')
    template = old_render[a:b]
    children_lo = old_render.index('[', old_render.index('children'))
    children_hi = old_render.rfind(']')
    output = stage/'Assets/models/maps/belltower/fountain-ornaments-v2/centre'
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source.with_suffix('.mtl'), output/'materials.mtl')
    nodes = []; rows = []; final_digest = hashlib.sha256()
    for number, part in enumerate(parts):
        name = f'centre_{number:03d}_{part["material"]}'
        assert re.fullmatch(r'[a-zA-Z0-9_]+', name)
        indices = part['faces']
        used = {kind: set(indices[offset::3]) for offset, kind in enumerate(C.KINDS)}
        maps = {kind: {old: new for new, old in enumerate(sorted(values), 1)} for kind, values in used.items()}
        target = output/(name+'.obj')
        with target.open('wb') as stream:
            stream.write(f'# Fountain ornaments v2 bounded centre import\nmtllib materials.mtl\no {name}\n'.encode())
            for kind in C.KINDS:
                for i in sorted(used[kind]): stream.write(data[kind][i])
            stream.write(f'usemtl {part["material"]}\n'.encode())
            for at in range(0, len(indices), 9):
                face = [indices[at+j:at+j+3] for j in (0, 3, 6)]
                tokens = [b'/'.join(str(maps[k][i]).encode() for k, i in zip(C.KINDS, row)) for row in face]
                stream.write(b'f '+b' '.join(tokens)+b'\n')
        check = C.tables(target); check_counts = {kind: len(values)-1 for kind, values in check.items()}
        for line in target.open('rb'):
            if line.startswith(b'f '):
                final_digest.update(part['material'].encode()+b'\n')
                for row in C.face_tokens(line, check_counts):
                    for kind, index in zip(C.KINDS, row): final_digest.update(check[kind][index])
        resource = target.relative_to(stage/'Assets').as_posix()
        node = re.sub(r'name = "[^"]+"', f'name = "{name}"', template, count=1)
        node = re.sub(r'filename = "[^"]+"', f'filename = "{resource}"', node, count=1)
        nodes.append(node)
        rows.append({'resource': resource, 'triangles': len(indices)//9, 'sha256': sha(target)})
    assert original_digest.digest() == final_digest.digest()
    render = old_render[:children_lo+1]+'\n'+',\n'.join(nodes)+'\n'+old_render[children_hi:]
    target = stage/vmdl.relative_to(ROOT)
    target.write_text(text[:lo]+render+text[hi:])
    assert target.read_text().replace(render, old_render, 1) == text
    return {'parts': rows, 'max_triangles_per_import': max(p['triangles'] for p in rows),
            'all_render_attributes_exact': True, 'material_remaps_and_physics_exact': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='revision1')
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'
    assert not (stage/'manifest.json').exists(), 'Keep each staging revision.'
    stage.mkdir(parents=True, exist_ok=True)
    old = original(); new = K.Model(); O.build(new)
    assert not new.boxes and not new.hulls and not new.props
    piece = stage/'ornaments.obj'; K.write_obj(piece, new, 'belltower_centre')
    relative = Path('Assets/models/maps/belltower/belltower_centre.obj')
    source = ROOT/relative; destination = stage/relative
    guarded = [source, source.with_suffix('.vmdl'), source.with_suffix('.mtl'),
               ROOT/'Assets/scenes/maps/Belltower/belltower.scene']
    guards = {p.relative_to(ROOT).as_posix(): sha(p) for p in guarded}
    preservation = patch(source, destination, keys(old), piece)
    shutil.copyfile(source.with_suffix('.mtl'), destination.with_suffix('.mtl'))
    imports = partition(destination, source.with_suffix('.vmdl'), stage)
    for relative, digest in guards.items(): assert sha(ROOT/relative) == digest
    manifest = {'revision': 'fountain-ornaments-v2', 'stage_revision': args.revision,
                'ornaments': {'lions': 4, 'large_lilies': 4, 'basin_lilies': 8},
                'preservation': preservation, 'imports': imports, 'files': {},
                'source_sha256': {p: sha(ROOT/p) for p in ['Tools/belltower_fountain_ornaments.py',
                    'Tools/belltower_stage_fountain_ornaments.py', 'Tools/belltower_fountain.py', 'Tools/map_kit.py',
                    LEGACY.relative_to(ROOT).as_posix(), O.lion_cache_path().relative_to(ROOT).as_posix()]},
                'protected_sha256': {p: digest for p, digest in guards.items() if not p.endswith(('.obj', '.vmdl'))},
                'scene_unchanged': True, 'collision_unchanged': True, 'water_geometry_and_materials_unchanged': True}
    for material in ['fountain_limestone', 'fountain_relief', 'fountain_bronze', 'fountain_water', 'fountain_jet']:
        p = ROOT/f'Assets/materials/belltower/{material}.vmat'
        manifest['protected_sha256'][p.relative_to(ROOT).as_posix()] = sha(p)
    for p in (stage/'Assets').rglob('*'):
        if not p.is_file(): continue
        relative = p.relative_to(stage)
        original_path = ROOT/relative
        before = sha(original_path) if original_path.exists() else None
        if before is not None:
            backup = stage/'before'/relative; backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original_path, backup); assert sha(backup) == before
        manifest['files'][relative.as_posix()] = {'source': p.relative_to(ROOT).as_posix(), 'before': before,
            'after': sha(p), 'backup': (stage/'before'/relative).relative_to(ROOT).as_posix() if before else None}
    (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'stage': str(stage), 'preservation': preservation,
                      'bounded_imports': len(imports['parts']), 'max_triangles_per_import': imports['max_triangles_per_import']}))


if __name__ == '__main__':
    main()
