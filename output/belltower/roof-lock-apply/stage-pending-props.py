"""Rebase reviewed roof, lock and scarecrow replacements onto current split imports."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import re
import shutil
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'stage-v1')
args = parser.parse_args()
OUT = args.out.resolve()
assert OUT.is_relative_to(ROOT / 'output/belltower/roof-lock-apply')
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_gazebo as G
import belltower_scarecrow as S
import belltower_stage_scarecrow as SS
import belltower_stage_padlocks as PS
import belltower_padlock as P
import belltower_compact_obj as C
import belltower_safe_imports as I

assert not OUT.exists(), 'Preserve prior staging evidence'
OUT.mkdir(parents=True)
report = {'revision': 'pending-garden-props-v1', 'files': {}, 'input_guards': {}, 'models': {}}


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def key(material, values):
    return material, frozenset(tuple(float(v) for v in p.split()) for p in values)


def keys(model):
    result = Counter()
    for material, polygons in model.polygons.items():
        for points, _ in polygons:
            p = [K.obj_vector(K.to_world(v)) for v in points]
            for i in range(1, len(p) - 1):
                result[key(material, (p[0], p[i], p[i + 1]))] += 1
    return result


def put(relative, data):
    relative = Path(relative)
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    installed = ROOT / relative
    before = sha(installed) if installed.exists() else None
    after = sha(target)
    if before == after:
        return
    report['files'][relative.as_posix()] = {'before': before, 'after': after}
    if before is not None:
        backup = OUT / 'before' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(installed, backup)
        assert sha(backup) == before


def scan_drops(path, wanted):
    positions = [None]
    counts = {'v': 0, 'vt': 0, 'vn': 0}
    paint = None
    found = Counter()
    drop = set()
    paints = {p for p, _ in wanted}
    for number, line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            positions.append(line[2:].strip().decode())
            counts['v'] += 1
        elif line.startswith(b'vt '): counts['vt'] += 1
        elif line.startswith(b'vn '): counts['vn'] += 1
        elif line.startswith(b'usemtl '): paint = line.split()[1].decode()
        elif line.startswith(b'f ') and paint in paints:
            values = [positions[int(t.split(b'/')[0])] for t in line.split()[1:]]
            k = key(paint, values)
            if k in wanted:
                drop.add(number)
                found[k] += 1
    return drop, found, counts


old_roof = K.Model()
B.cone(old_roof, (-500, -1130), 72, 48, 102, 'copper', sides=6, turn=0.)
new_roof = K.Model(); G.build(new_roof); D.configure(new_roof)
old_lock, new_lock = PS.models()
old_crow = SS.original()
new_crow = K.Model(); S.build(new_crow, B.Place((-1590, -1345, B.GARDEN_Z), 0)); D.configure(new_crow)
models = {'roof': (old_roof, new_roof), 'locks': (old_lock, new_lock), 'scarecrow': (old_crow, new_crow)}
assert [a.triangle_count() for a, b in models.values()] == [10, 264, 86]
assert [b.triangle_count() for a, b in models.values()] == [6052, 11790, 7480]
remaps = {**{p: f'{G.RESOURCE}/{p}.vmat' for p in (G.COPPER, G.SEAM)}, P.STEEL: P.STEEL_MATERIAL, **S.MATERIALS}
for record in ['Sources/Belltower/gazebo/roof-v1.json', 'Sources/Belltower/gardens/shed-padlock-v1.json', 'Sources/Belltower/scarecrows/stitched-scarecrow-v1.json']:
    meta = json.loads((ROOT / record).read_text())
    generator = ROOT / meta['generator']
    expected = meta.get('generator_sha256')
    if expected: assert sha(generator) == expected, generator
    report['input_guards'][generator.relative_to(ROOT).as_posix()] = sha(generator)
for paint, text in G.materials().items(): put(Path('Assets') / G.RESOURCE / (paint + '.vmat'), text.encode())
put(Path('Assets') / P.STEEL_MATERIAL, PS.steel_material().encode())
for paint, material in S.MATERIALS.items():
    assert (ROOT / 'Assets' / material).exists(), material
    report['input_guards']['Assets/' + material] = sha(ROOT / 'Assets' / material)

for side in ('west', 'east'):
    name = f'belltower_{side}'
    relative = Path(f'Assets/models/maps/belltower/{name}.obj')
    source = ROOT / relative
    before_hash = sha(source)
    vmdl = source.with_suffix('.vmdl')
    text = vmdl.read_text()
    list_lo, list_hi = I.span(text, '_class = "RenderMeshList"')
    render_list = text[list_lo:list_hi]
    file_lo, file_hi = I.span(render_list, '_class = "RenderMeshFile"')
    template = render_list[file_lo:file_hi]
    wanted = Counter()
    pieces = []
    extra_nodes = []
    for label, (old, new) in models.items():
        if side == 'east':
            paints = B.EAST_PAINTS if label == 'scarecrow' else None
            old = old.mirrored(paints) if paints is not None else old.mirrored()
            new = new.mirrored(paints) if paints is not None else new.mirrored()
        wanted.update(keys(old))
        part_rel = Path(f'Assets/models/maps/belltower/pending-garden-v1/{side}/{name}-{label}.obj')
        part = OUT / part_rel
        part.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(part, new, name)
        # Verify newly exported positions, UVs and normals are finite.
        for line in part.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')):
                assert np.isfinite(list(map(float, line.split()[1:]))).all()
        pieces.append(part)
        for p in (part, part.with_suffix('.mtl')):
            report['files'][p.relative_to(OUT).as_posix()] = {'before': sha(ROOT / p.relative_to(OUT)) if (ROOT / p.relative_to(OUT)).exists() else None, 'after': sha(p)}
        node = re.sub(r'name = "[^"]+"', f'name = "{name}_{label}_replacement"', template, count=1)
        node = re.sub(r'filename = "[^"]+"', f'filename = "{part_rel.relative_to("Assets").as_posix()}"', node, count=1)
        extra_nodes.append(node)
    drop, found, counts = scan_drops(source, wanted)
    assert found == wanted and len(drop) == 360, (side, sum(found.values()), sum(wanted.values()))
    # Preserve every original table entry and unrelated face in the canonical generator source.
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    appended_tables = []
    appended_faces = []
    running = counts.copy()
    for piece in pieces:
        local = {'v': 0, 'vt': 0, 'vn': 0}
        for line in piece.open('rb'):
            kind = line.split(b' ', 1)[0].decode(errors='ignore')
            if kind in local:
                appended_tables.append(line); local[kind] += 1
            elif line.startswith(b'usemtl '): appended_faces.append(line)
            elif line.startswith(b'f '):
                tokens = []
                for t in line.split()[1:]:
                    a, b, c = map(int, t.split(b'/'))
                    tokens.append(f'{a+running["v"]}/{b+running["vt"]}/{c+running["vn"]}')
                appended_faces.append(('f ' + ' '.join(tokens) + '\n').encode())
        for k, value in local.items(): running[k] += value
    with source.open('rb') as original, target.open('wb') as updated:
        inserted = False
        for number, line in enumerate(original):
            if not inserted and line.startswith(b'usemtl '): updated.writelines(appended_tables); inserted = True
            if number not in drop: updated.write(line)
        updated.writelines(appended_faces)
    assert sha(source) == before_hash
    put(relative, target.read_bytes())
    # Remove the same old faces from the actual bounded renderer inputs.
    bounded_found = Counter()
    removed_nodes = []
    for resource in re.findall(r'filename = "([^"]+)"', render_list):
        path = ROOT / 'Assets' / resource
        report['input_guards'][path.relative_to(ROOT).as_posix()] = sha(path)
        if not any(path.stem.endswith('_' + p) for p, _ in wanted): continue
        part_drop, part_found, _ = scan_drops(path, wanted)
        if not part_drop: continue
        bounded_found.update(part_found)
        face_count = sum(line.startswith(b'f ') for line in path.open('rb'))
        if face_count == len(part_drop):
            marker = 'filename = "' + resource + '"'
            at = render_list.index(marker)
            # The node's top-level brace precedes its class marker; use the verified parser on its suffix.
            class_at = render_list.rfind('_class = "RenderMeshFile"', 0, at)
            node_start = render_list.rfind('{', 0, class_at)
            _, node_end = I.span(render_list[node_start:], '_class = "RenderMeshFile"')
            removed_nodes.append(render_list[node_start:node_start + node_end])
        else:
            filtered = OUT / 'filtered' / path.name
            filtered.parent.mkdir(parents=True, exist_ok=True)
            with path.open('rb') as incoming, filtered.open('wb') as dest:
                for number, line in enumerate(incoming):
                    if number not in part_drop: dest.write(line)
            compacted = OUT / path.relative_to(ROOT)
            proof = C.compact(filtered, compacted, deduplicate=True)
            assert proof['all_face_material_position_uv_normal_bytes_identical']
            put(path.relative_to(ROOT), compacted.read_bytes())
    assert bounded_found == wanted, (side, bounded_found - wanted, wanted - bounded_found)
    for node in removed_nodes:
        assert render_list.count(node) == 1
        render_list = render_list.replace(node + ',', '', 1) if node + ',' in render_list else render_list.replace(node, '', 1)
    end = render_list.rfind(']')
    prefix = render_list[:end].rstrip()
    if not prefix.endswith(','): prefix += ','
    render_list = prefix + '\n\t\t\t\t\t' + ',\n\t\t\t\t\t'.join(extra_nodes) + '\n\t\t\t\t' + render_list[end:]
    updated_vmdl = text[:list_lo] + render_list + text[list_hi:]
    anchor = next(l for l in updated_vmdl.splitlines(keepends=True) if 'from = "iron_black.vmat"' in l)
    space = anchor[:len(anchor) - len(anchor.lstrip())]
    additions = ''.join(space + f'{{ from = "{p}.vmat" to = "{m}" }},\n' for p, m in remaps.items() if f'from = "{p}.vmat"' not in updated_vmdl)
    updated_vmdl = updated_vmdl.replace(anchor, additions + anchor, 1)
    phys_a, phys_b = I.span(text, '_class = "PhysicsShapeList"')
    phys_c, phys_d = I.span(updated_vmdl, '_class = "PhysicsShapeList"')
    assert text[phys_a:phys_b] == updated_vmdl[phys_c:phys_d]
    put(vmdl.relative_to(ROOT), updated_vmdl.encode())
    mtl = source.with_suffix('.mtl')
    original_mtl = mtl.read_bytes()
    extra_mtl = b''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n'.encode() for p in remaps if f'newmtl {p}\n'.encode() not in original_mtl)
    put(mtl.relative_to(ROOT), original_mtl + extra_mtl)
    report['models'][side] = {'removed_triangles': 360, 'added_triangles': sum(b.triangle_count() for a, b in models.values()),
        'only_reviewed_props_replaced': True, 'canonical_non_target_obj_bytes_preserved': True,
        'split_non_target_face_attributes_preserved': True, 'physics_bytes_identical': True,
        'new_imports': 3, 'empty_old_imports_removed': len(removed_nodes)}
    print(json.dumps({'side': side, **report['models'][side]}), flush=True)
for path in ['Tools/map_kit.py', 'Tools/belltower_furniture.py', 'Tools/belltower_map.py']:
    report['input_guards'][path] = sha(ROOT / path)
(OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'staged_files': len(report['files']), 'guarded_inputs': len(report['input_guards'])}), flush=True)
