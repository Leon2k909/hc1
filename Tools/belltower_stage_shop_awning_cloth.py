"""Stage wall-mounted awnings only, including their actual bounded render imports.

No Assets writes. Exact legacy matching protects concurrent town/stone edits.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_shop_awning_cloth as Cloth
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/shop-awning-cloth-v1'
LEGACY = ROOT/'Sources/Belltower/props/shop-awning-cloth-v1/legacy-awning.py.txt'


def sha(p):
    with p.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def current_hook():
    source = (ROOT/'Tools/belltower_map.py').read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'awning')
    return ast.get_source_segment(source, node)


def models():
    scope = B.__dict__.copy()
    exec(compile(LEGACY.read_text(), str(LEGACY), 'exec'), scope)
    legacy = scope['awning']
    old, new, placements = K.Model(), K.Model(), []

    class Sink(K.Model):
        def polygon(self, *args, **kwargs): pass

    def record(model, wall, r0, r1, z, reach, paint, name=None):
        legacy(old, wall, r0, r1, z, reach, paint, name)
        Cloth.build(new, wall, r0, r1, z, reach, paint, name)
        depth, sign = wall.outer()
        placements.append({'axis': wall.axis, 'depth': depth, 'sign': sign, 'r0': r0, 'r1': r1,
                           'z': z, 'reach': reach, 'paint': paint, 'name': name})

    # Only placement/name logic is needed. These deterministic drawing helpers
    # do not consume the west_houses RNG; omit their unrelated geometry work.
    originals = []
    def replace(obj, name, value):
        originals.append((obj, name, getattr(obj, name))); setattr(obj, name, value)
    no_op = lambda *a, **kw: None
    replace(B, 'awning', record)
    for name in ['gable_roof', 'balcony', 'window_box', 'door_pot', 'climb_ivy', 'ivy', 'wall_lantern',
                 'downpipe', 'shutters_open']:
        replace(B, name, no_op)
    replace(B, 'street_plaque', lambda *a, **kw: True)
    for name in ['window_sill', 'window_surround', 'shutter', 'street_door', 'cornice']:
        replace(B.Architecture, name, no_op)
    old_shop_index = B._shops[0]
    try:
        B._shops[0] = 0
        B.west_houses(Sink(), np.random.default_rng(2024))
    finally:
        B._shops[0] = old_shop_index
        for obj, name, value in reversed(originals): setattr(obj, name, value)
    assert placements and not new.boxes and not new.hulls and not new.props
    for paint, faces in new.polygons.items():
        for i, (points, normal) in enumerate(faces):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            assert (paint, i) in new.polygon_uvs and (paint, i) in new.polygon_normals
            assert np.dot(np.cross(points[1]-points[0], points[2]-points[0]), normal) > 1e-8
    assert new.triangle_count() <= 65000
    return old, new, placements


def point(value): return tuple(int(round(float(v)*1000)) for v in value.split())


def keys(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for points, normal in polygons:
            vertices = [point(K.obj_vector(K.to_world(p))) for p in points]
            for i in range(1, len(vertices)-1):
                result[(paint.encode(), frozenset((vertices[0], vertices[i], vertices[i+1])))] += 1
    return result


def patch(source, target, wanted, addition=None):
    source_hash = sha(source)
    positions = {p for paint, face in wanted for p in face}
    sparse = {}; count = {'v': 0, 'vt': 0, 'vn': 0}; found = Counter(); drop = set(); paint = None; face_count = 0
    paints = {p for p, f in wanted}
    for index, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            count['v'] += 1; p = point(line[2:].decode())
            if p in positions: sparse[count['v']] = p
        elif line.startswith(b'vt '): count['vt'] += 1
        elif line.startswith(b'vn '): count['vn'] += 1
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f '):
            face_count += 1
            if paint not in paints: continue
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = paint, frozenset(sparse[i] for i in indices)
                if key in wanted: drop.add(index); found[key] += 1
    if not drop:
        assert sha(source) == source_hash
        return {'found': found, 'remaining_faces': face_count, 'changed': False}
    tables, faces = [], []
    if addition:
        for line in addition.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')): tables.append(line)
            elif line.startswith(b'usemtl '): faces.append(line)
            elif line.startswith(b'f '):
                tokens = [b'/'.join(str(int(i)+count[k]).encode() for k, i in zip(('v', 'vt', 'vn'), t.split(b'/')))
                          for t in line.split()[1:]]
                faces.append(b'f '+b' '.join(tokens)+b'\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    retained = hashlib.sha256(); inserted = not bool(tables)
    with target.open('wb') as dest:
        for index, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): dest.writelines(tables); inserted = True
            if index not in drop: dest.write(line); retained.update(line)
        dest.writelines(faces)
    assert inserted
    # Independent byte proof: only inserted tables/appended triangles and
    # the exactly matched legacy awning triangles may differ.
    raw = target.read_bytes()
    if tables: raw = raw.replace(b''.join(tables), b'', 1)
    if faces: raw = raw[:-len(b''.join(faces))]
    expected = b''.join(line for i, line in enumerate(source.open('rb')) if i not in drop)
    assert raw == expected
    assert sha(source) == source_hash, ('Concurrent mesh edit', source)
    return {'found': found, 'remaining_faces': face_count-len(drop), 'changed': True,
            'removed': len(drop), 'unrelated_bytes_sha256': retained.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--revision', required=True)
    args = parser.parse_args(); assert re.fullmatch(r'[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'; assert not (stage/'manifest.json').exists(); stage.mkdir(parents=True, exist_ok=True)
    old, new, placements = models()
    report = {'revision': 'shop-awning-cloth-v1', 'stage_revision': args.revision, 'files': {}, 'models': {},
              'awnings_per_half': len(placements), 'placements_west': placements,
              'new_triangles_per_half': new.triangle_count(), 'old_triangles_per_half': old.triangle_count(),
              'source_sha256': {}, 'protected_sha256': {}, 'scene_changed': False, 'collision_changed': False,
              'map_awning_hook': current_hook()}
    for p in ['Tools/belltower_shop_awning_cloth.py', 'Tools/belltower_stage_shop_awning_cloth.py', LEGACY.relative_to(ROOT).as_posix()]:
        report['source_sha256'][p] = sha(ROOT/p)
    input_hashes = {}
    for side in ['west', 'east']:
        previous = old if side == 'west' else old.mirrored(B.EAST_PAINTS)
        candidate = new if side == 'west' else new.mirrored(B.EAST_PAINTS)
        candidate.tile_overrides.update({paint: 48. for paint in candidate.polygons})
        wanted = keys(previous)
        name = 'belltower_'+side
        obj = ROOT/f'Assets/models/maps/belltower/{name}.obj'
        vmdl = obj.with_suffix('.vmdl'); mtl = obj.with_suffix('.mtl')
        before_hashes = {p: sha(p) for p in [obj, vmdl, mtl]}
        input_hashes.update(before_hashes)
        piece = stage/f'Assets/models/maps/belltower/shop-awning-cloth-v1/{side}.obj'
        piece.parent.mkdir(parents=True, exist_ok=True); K.write_obj(piece, candidate, name)
        patched = patch(obj, stage/obj.relative_to(ROOT), wanted, piece)
        assert patched['found'] == wanted, ('Canonical awning mismatch', side, wanted-patched['found'])
        text = vmdl.read_bytes().decode('utf-8')
        lo, hi = span(text, '_class = "RenderMeshList"'); render = text[lo:hi]
        node_lo, node_hi = span(render, '_class = "RenderMeshFile"'); template = render[node_lo:node_hi]
        imported = Counter(); changed = []; omitted = []
        paths = re.findall(r'filename = "([^"]+\.obj)"', render)
        for relative in paths:
            if not any(word in Path(relative).stem for word in ['awning_', 'valance_', 'letters_']): continue
            path = ROOT/'Assets'/relative
            input_hashes[path] = sha(path)
            row = patch(path, stage/path.relative_to(ROOT), wanted)
            if not row['changed']: continue
            imported.update(row['found'])
            if row['remaining_faces'] == 0:
                # Leave the now-unreferenced old source in place; avoid importing
                # an empty mesh or deleting anyone else's files.
                (stage/path.relative_to(ROOT)).unlink()
                a, b = span(render, 'filename = "'+relative+'"')
                if render[b:b+1] == ',': b += 1
                render = render[:a]+render[b:]; omitted.append(relative)
            else: changed.append(relative)
        assert imported == wanted, ('Active bounded imports differ', side, wanted-imported)
        node = re.sub(r'name = "[^"]+"', f'name = "shop_awnings_{side}"', template, count=1)
        node = re.sub(r'filename = "[^"]+"', f'filename = "models/maps/belltower/shop-awning-cloth-v1/{side}.obj"', node, count=1)
        end = render.rfind(']'); assert end > 0
        prefix = render[:end].rstrip()
        if not prefix.endswith(('[', ',')): prefix += ','
        render = prefix+'\n'+node+',\n'+render[end:]
        target = stage/vmdl.relative_to(ROOT); target.write_bytes((text[:lo]+render+text[hi:]).encode('utf-8'))
        assert target.read_bytes().decode().replace(render, text[lo:hi], 1) == text
        for p, digest in before_hashes.items(): assert sha(p) == digest, ('Concurrent input change', p)
        report['protected_sha256'][mtl.relative_to(ROOT).as_posix()] = sha(mtl)
        report['models'][side] = {'canonical_removed': patched['removed'], 'unrelated_obj_bytes_exact': True,
            'unrelated_obj_bytes_sha256': patched['unrelated_bytes_sha256'], 'bounded_imports_patched': changed,
            'empty_old_import_nodes_omitted': omitted, 'physics_and_remaps_bytes_exact': True}
    # The scene is not an input or target; it may be in use by the parent chat.
    # The publisher snapshots editor state and scene hash around its short write.
    for p in (stage/'Assets').rglob('*'):
        if not p.is_file(): continue
        relative = p.relative_to(stage); installed = ROOT/relative
        before = sha(installed) if installed.exists() else None
        if installed in input_hashes:
            assert before == input_hashes[installed], ('Shared input changed after staging', installed)
        backup = stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(installed, backup); assert sha(backup) == before
        report['files'][relative.as_posix()] = {'source': p.relative_to(ROOT).as_posix(), 'before': before,
            'after': sha(p), 'backup': backup.relative_to(ROOT).as_posix() if before else None}
    (stage/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'awnings_per_half': len(placements), 'old_triangles_per_half': old.triangle_count(),
                      'new_triangles_per_half': new.triangle_count(), 'targets': len(report['files']), 'stage': str(stage)}))


if __name__ == '__main__': main()
