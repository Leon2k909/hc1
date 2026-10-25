"""Stage material-preserving, bounded OBJ imports for the two town models.

Each import contains at most 100,000 triangles. The existing VMDL resources,
scene references, material remaps and physics remain in place. This tool does
not publish assets; inspect the manifest before installation with editor closed.
"""
import argparse
from array import array
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil

import belltower_compact_obj as C

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 100_000


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def span(text, marker):
    start = text.rfind('{', 0, text.index(marker))
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if char == '"' and not escaped:
            quoted = not quoted
        if not quoted:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1
        escaped = char == '\\' and not escaped
    raise ValueError('Unbalanced ModelDoc node')


def stage(side, output):
    directory = ROOT / 'Assets/models/maps/belltower'
    source = directory / f'belltower_{side}.obj'
    vmdl = source.with_suffix('.vmdl')
    mtl = source.with_suffix('.mtl')
    guards = {p.relative_to(ROOT).as_posix(): sha(p) for p in (source, vmdl, mtl)}
    data = C.tables(source)
    counts = {kind: len(values) - 1 for kind, values in data.items()}
    parts = []
    current = None
    material = None
    original_digest = hashlib.sha256()
    for line in source.open('rb'):
        if line.startswith(b'usemtl '):
            material = line.split()[1].decode()
            current = None
        elif line.startswith(b'f '):
            if current is None or len(current['faces']) // 9 >= LIMIT:
                current = {'material': material, 'faces': array('I')}
                parts.append(current)
            face = C.face_tokens(line, counts)
            current['faces'].extend(i for row in face for i in row)
            original_digest.update(material.encode() + b'\n')
            for row in face:
                for kind, index in zip(C.KINDS, row):
                    original_digest.update(data[kind][index])
    part_rows = []
    final_digest = hashlib.sha256()
    nodes = []
    text = vmdl.read_text()
    lo, hi = span(text, '_class = "RenderMeshList"')
    render_list = text[lo:hi]
    mesh_lo, mesh_hi = span(render_list, '_class = "RenderMeshFile"')
    template = render_list[mesh_lo:mesh_hi]
    children_lo = render_list.index('[', render_list.index('children'))
    children_hi = render_list.rfind(']')
    assert children_lo < children_hi
    asset_dir = Path(f'Assets/models/maps/belltower/compiler-safe/{side}')
    target_dir = output / asset_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mtl, target_dir / 'materials.mtl')
    for number, part in enumerate(parts):
        name = f'{side}_{number:03d}_{part["material"]}'
        assert re.fullmatch(r'[a-zA-Z0-9_]+', name)
        target = target_dir / (name + '.obj')
        indices = part['faces']
        used = {kind: set(indices[offset::3]) for offset, kind in enumerate(C.KINDS)}
        maps = {kind: {old: new for new, old in enumerate(sorted(values), 1)} for kind, values in used.items()}
        with target.open('wb') as stream:
            stream.write(f'# Belltower bounded compiler import\nmtllib materials.mtl\no {name}\n'.encode())
            for kind in C.KINDS:
                for index in sorted(used[kind]):
                    stream.write(data[kind][index])
            stream.write(f'usemtl {part["material"]}\n'.encode())
            for at in range(0, len(indices), 9):
                face = [indices[at + j:at + j + 3] for j in (0, 3, 6)]
                tokens = [b'/'.join(str(maps[k][i]).encode() for k, i in zip(C.KINDS, row)) for row in face]
                stream.write(b'f ' + b' '.join(tokens) + b'\n')
        # Read the staged file independently and compare resolved geometry.
        imported = C.tables(target)
        imported_counts = {kind: len(values) - 1 for kind, values in imported.items()}
        for line in target.open('rb'):
            if line.startswith(b'f '):
                final_digest.update(part['material'].encode() + b'\n')
                for row in C.face_tokens(line, imported_counts):
                    for kind, index in zip(C.KINDS, row):
                        final_digest.update(imported[kind][index])
        rel = target.relative_to(output)
        resource = rel.relative_to('Assets').as_posix()
        node = re.sub(r'name = "[^"]+"', f'name = "{name}"', template, count=1)
        node = re.sub(r'filename = "[^"]+"', f'filename = "{resource}"', node, count=1)
        nodes.append(node)
        part_rows.append({'asset': rel.as_posix(), 'sha256': sha(target), 'material': part['material'],
            'faces': len(indices) // 9, 'positions': imported_counts[b'v']})
    assert final_digest.digest() == original_digest.digest()
    updated_list = (render_list[:children_lo + 1] + '\n\t\t\t\t\t' +
        ',\n\t\t\t\t\t'.join(nodes) + '\n\t\t\t\t' + render_list[children_hi:])
    updated = text[:lo] + updated_list + text[hi:]
    target_vmdl = output / vmdl.relative_to(ROOT)
    target_vmdl.parent.mkdir(parents=True, exist_ok=True)
    target_vmdl.write_text(updated)
    assert all(sha(ROOT / p) == digest for p, digest in guards.items())
    return {'input_guards': guards, 'parts': part_rows, 'parts_count': len(parts),
        'faces': sum(p['faces'] for p in part_rows), 'max_faces_per_import': max(p['faces'] for p in part_rows),
        'face_material_position_uv_normal_sha256': final_digest.hexdigest(),
        'all_renderable_triangles_and_attributes_exact': True,
        'vmdl_original_prefix_suffix_and_physics_exact': True,
        'vmdl': vmdl.relative_to(ROOT).as_posix(), 'vmdl_after_sha256': sha(target_vmdl),
        'mtl': (asset_dir / 'materials.mtl').as_posix(), 'mtl_sha256': sha(target_dir / 'materials.mtl')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    assert output.is_relative_to(ROOT / 'output/belltower')
    assert not output.exists(), 'Keep prior staging evidence'
    output.mkdir(parents=True)
    report = {'revision': 'bounded-town-imports-v1', 'models': {}}
    for side in ('east', 'west'):
        row = stage(side, output)
        report['models'][side] = row
        print(json.dumps({k: v for k, v in row.items() if k != 'parts'}), flush=True)
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
