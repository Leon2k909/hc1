"""Stage the church's three front windows without rebuilding the town or fountain."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import belltower_map as B
import belltower_church_windows as W
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/church-windows-v1'
PRIVATE = 'Assets/models/maps/belltower/church-windows-v1'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def original():
    model = K.Model(); wall = W.front_wall()
    for o in wall.openings:
        B.pane(model, wall, o, 'glass', 5.)
        B.frame(model, wall, o, 'iron_black', 4., bar=2.)
    B.slab_at(model, wall, -170., 170., 0., 8., 275., 287., 'ashlar_grey')
    return model


def point(value):
    return tuple(round(float(v)*1000) for v in value.split())


def keys(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for points, normal in polygons:
            p = [point(K.obj_vector(K.to_world(v))) for v in points]
            for j in range(1, len(p)-1): result[(paint.encode(), frozenset((p[0], p[j], p[j+1])))] += 1
    return result


def patch(source, target, wanted, addition=None):
    positions = {p for paint, face in wanted for p in face}
    sparse = {}; counts = {b'v': 0, b'vt': 0, b'vn': 0}; paint = None; found = Counter(); drop = set()
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts[b'v'] += 1; p = point(line[2:].decode())
            if p in positions: sparse[counts[b'v']] = p
        elif line.startswith(b'vt '): counts[b'vt'] += 1
        elif line.startswith(b'vn '): counts[b'vn'] += 1
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f ') and paint in (b'glass', b'iron_black', b'ashlar_grey'):
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = (paint, frozenset(sparse[i] for i in indices))
                if key in wanted: found[key] += 1; drop.add(number)
    if not drop: return found
    tables, faces = [], []
    if addition:
        for line in addition.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')): tables.append(line)
            elif line.startswith(b'usemtl '): faces.append(line)
            elif line.startswith(b'f '):
                tokens = [b'/'.join(str(int(value)+counts[kind]).encode() for kind, value in zip((b'v', b'vt', b'vn'), token.split(b'/')))
                          for token in line.split()[1:]]
                faces.append(b'f '+b' '.join(tokens)+b'\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    inserted = False; before = hashlib.sha256()
    with target.open('wb') as output:
        for number, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): output.writelines(tables); inserted = True
            if number not in drop: output.write(line); before.update(line)
        output.writelines(faces)
    assert inserted
    raw = target.read_bytes()
    if tables: raw = raw.replace(b''.join(tables), b'', 1)
    if faces: raw = raw[:-len(b''.join(faces))]
    assert hashlib.sha256(raw).hexdigest() == before.hexdigest(), 'Unrelated OBJ attributes changed.'
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='revision1')
    args = parser.parse_args(); assert re.fullmatch('[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'; assert not (stage/'manifest.json').exists()
    stage.mkdir(parents=True, exist_ok=True)
    old = original(); wanted = keys(old); new = K.Model(); wall = W.front_wall()
    for o in wall.openings: W.build(new, wall, o)
    W.front_band(new, wall)
    assert not new.boxes and not new.hulls and not new.props
    private = stage/PRIVATE; private.mkdir(parents=True, exist_ok=True)
    addition = private/'windows.obj'; K.write_obj(addition, new, 'belltower_centre')
    # Existing imports are preserved individually; only three matching imports
    # receive private copies. Every fountain import remains an untouched input.
    vmdl = ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl'
    text = vmdl.read_bytes().decode()
    lo, hi = span(text, '_class = "RenderMeshList"'); render = text[lo:hi]
    mesh_lo, mesh_hi = span(render, '_class = "RenderMeshFile"'); template = render[mesh_lo:mesh_hi]
    sources = re.findall(r'filename = "([^"]+)"', render)
    assert len(sources) > 10, 'The bounded centre imports are required.'
    found = Counter(); replaced = []; protected = {}
    updated = text
    for name in sources:
        source = ROOT/'Assets'/name
        protected[source.relative_to(ROOT).as_posix()] = sha(source)
        if not any(name.endswith('_'+p+'.obj') for p in ('ashlar_grey', 'glass', 'iron_black')):
            protected[source.relative_to(ROOT).as_posix()] = sha(source); continue
        target = private/source.name
        matched = patch(source, target, wanted)
        if matched:
            found.update(matched)
            resource = target.relative_to(stage/'Assets').as_posix()
            assert updated.count('filename = "'+name+'"') == 1
            updated = updated.replace('filename = "'+name+'"', 'filename = "'+resource+'"')
            replaced.append(name)
        else:
            protected[source.relative_to(ROOT).as_posix()] = sha(source)
    assert found == wanted, ('Installed window triangles differ', sum((wanted-found).values()), sum((found-wanted).values()))
    canonical = ROOT/'Assets/models/maps/belltower/belltower_centre.obj'
    target = stage/canonical.relative_to(ROOT)
    assert patch(canonical, target, wanted, addition) == wanted
    mtl = canonical.with_suffix('.mtl')
    raw_mtl = mtl.read_bytes()
    extra_mtl = b''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n'.encode() for p in W.MATERIALS)
    assert all(f'newmtl {p}\n'.encode() not in raw_mtl for p in W.MATERIALS)
    target.with_suffix('.mtl').write_bytes(raw_mtl+extra_mtl)
    (private/'materials.mtl').write_bytes(raw_mtl)
    # The addition has its own windows.mtl, with the exact new material names.
    node = re.sub(r'name = "[^"]+"', 'name = "church_front_windows_v1"', template, count=1)
    node = re.sub(r'filename = "[^"]+"', 'filename = "'+addition.relative_to(stage/'Assets').as_posix()+'"', node, count=1)
    start, end = span(updated, '_class = "RenderMeshList"')
    local = updated[start:end]; at = local.rfind(']')
    prefix = local[:at].rstrip()
    local = prefix+('' if prefix.endswith(',') else ',')+'\n'+node+',\n'+local[at:]
    updated = updated[:start]+local+updated[end:]
    anchor = re.search(r'remaps\s*=\s*\[', updated)
    remaps = '\n'+''.join('{ from = "'+p+'.vmat" to = "'+path+'" },\n' for p, path in W.MATERIALS.items())
    updated = updated[:anchor.end()]+remaps+updated[anchor.end():]
    physics_old = span(text, '_class = "PhysicsShapeList"'); physics_new = span(updated, '_class = "PhysicsShapeList"')
    assert text[slice(*physics_old)] == updated[slice(*physics_new)]
    staged_vmdl = stage/vmdl.relative_to(ROOT); staged_vmdl.write_bytes(updated.encode())
    for name, material in W.glass_materials().items():
        p = stage/f'Assets/materials/belltower/church-windows-v1/{name}.vmat'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(material)
    for p in [ROOT/'Assets/scenes/maps/Belltower/belltower.scene', mtl]:
        if p != mtl: protected[p.relative_to(ROOT).as_posix()] = sha(p)
    manifest = {'revision': 'church-windows-v1', 'stage_revision': args.revision, 'windows': 3,
        'old_triangles': old.triangle_count(), 'new_triangles': new.triangle_count(),
        'only_target_window_faces_removed': True, 'unrelated_obj_bytes_exact': True,
        'physics_exact': True, 'scene_unchanged': True, 'fountain_imports_unchanged': True,
        'replaced_imports': replaced, 'protected_sha256': protected, 'files': {},
        'source_sha256': {p: sha(ROOT/p) for p in ['Tools/belltower_map.py', 'Tools/belltower_church_windows.py', 'Tools/belltower_stage_church_windows.py']}}
    for p in (stage/'Assets').rglob('*'):
        if not p.is_file(): continue
        relative = p.relative_to(stage); installed = ROOT/relative
        before = sha(installed) if installed.exists() else None
        backup = stage/'before'/relative
        if before: backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(installed, backup); assert sha(backup) == before
        manifest['files'][relative.as_posix()] = {'before': before, 'after': sha(p),
            'source': p.relative_to(ROOT).as_posix(), 'backup': backup.relative_to(ROOT).as_posix() if before else None}
    for p, digest in protected.items(): assert sha(ROOT/p) == digest
    (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'stage': str(stage), 'old_triangles': old.triangle_count(), 'new_triangles': new.triangle_count(),
                      'changed_original_imports': replaced, 'fountain_preserved': True, 'collision_preserved': True}))


if __name__ == '__main__': main()
