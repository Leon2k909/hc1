"""Stage only Belltower's buried town-wall faces, preserving live model edits.

Match the original wall triangles by position, normal and material. Everything
else in the existing OBJ is retained, including its UVs and collision resources.
Publish the resulting files through the native editor, using the manifest hashes.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import numpy as np
import belltower_map as B
import belltower_wall_cleanup as W

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/wall-v2'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(paint, points, normal):
    return paint, tuple(sorted(tuple(np.round(p, 3)) for p in points)), tuple(np.round(normal, 3))


def to_obj(p):
    return np.array((-p[0], p[2], p[1]), float)


def read_obj(path):
    vertices, uvs, normals, faces, header = [], [], [], [], []
    paint = None
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            vertices.append(np.array(list(map(float, line.split()[1:]))))
        elif line.startswith('vt '):
            uvs.append(np.array(list(map(float, line.split()[1:3]))))
        elif line.startswith('vn '):
            normals.append(np.array(list(map(float, line.split()[1:]))))
        elif line.startswith('usemtl '):
            paint = line.split()[1]
        elif line.startswith('f '):
            indices = [tuple(int(i)-1 for i in corner.split('/')) for corner in line.split()[1:]]
            if len(indices) != 3:
                raise ValueError('Expected triangulated map source')
            faces.append((paint, indices, line))
        else:
            header.append(line)
    return vertices, uvs, normals, faces, header


def stage_half(name, mirrored, base):
    resource = f'models/maps/belltower/belltower_{name}.obj'
    source = OUT / 'before-assets/Assets' / resource
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes((ROOT / 'Assets' / resource).read_bytes())
    vertices, uvs, normals, faces, header = read_obj(source)
    lookup = defaultdict(list)
    for i, (paint, corners, _) in enumerate(faces):
        lookup[key(paint, [vertices[v] for v, _, _ in corners], normals[corners[0][2]])].append(i)
    replacements, deleted = {}, set()
    matched, removed_area = 0, 0.
    for paint in ('rubble', 'ashlar', 'ashlar_grey'):
        for points, normal in base.polygons[paint]:
            pieces = W.visible_pieces(points)
            old_area = W.polygon_area(points)
            new_area = sum(W.polygon_area(p) for p in pieces)
            if abs(old_area-new_area) < .001:
                continue
            transformed = [to_obj(p * (-1, 1, 1) if mirrored else p) for p in points]
            obj_normal = to_obj(normal * (-1, 1, 1) if mirrored else normal)
            indices = []
            for k in range(1, len(points)-1):
                signature = key(paint, [transformed[j] for j in (0, k, k+1)], obj_normal)
                options = lookup.get(signature, [])
                if not options:
                    raise ValueError(f'Original {name} wall face no longer matches: {paint} {points}')
                indices.append(options.pop())
            if deleted.intersection(indices):
                raise ValueError('Wall triangle matched twice')
            deleted.update(indices)
            matched += len(indices)
            removed_area += old_area-new_area
            # Fit the existing planar UV transform instead of changing the
            # model's texture origin, including the mirrored half's UVs.
            corners = faces[indices[0]][1]
            affine = np.array([list(vertices[v])+[1.] for v, _, _ in corners])
            texcoords = np.array([uvs[t] for _, t, _ in corners])
            uv_fit = np.linalg.lstsq(affine, texcoords, rcond=None)[0]
            normal_index = corners[0][2]
            inserted = []
            for piece in pieces:
                if mirrored:
                    piece = [p * (-1, 1, 1) for p in piece[::-1]]
                obj_piece = [to_obj(p) for p in piece]
                new_corners = []
                for p in obj_piece:
                    uv = np.append(p, 1.) @ uv_fit
                    new_corners.append((len(vertices), len(uvs), normal_index))
                    vertices.append(p)
                    uvs.append(uv)
                for k in range(1, len(new_corners)-1):
                    triangle = [new_corners[j] for j in (0, k, k+1)]
                    inserted.append('f '+' '.join('/'.join(str(i+1) for i in c) for c in triangle))
            replacements[min(indices)] = inserted
    if not matched:
        raise ValueError('No buried wall faces matched')
    output = header
    output += ['v '+' '.join(f'{v:.3f}' for v in p) for p in vertices]
    output += ['vt '+' '.join(f'{v:.5f}' for v in p) for p in uvs]
    output += ['vn '+' '.join(f'{v:.3f}' for v in p) for p in normals]
    last_paint, after_count = None, 0
    for i, (paint, _, line) in enumerate(faces):
        lines = replacements.get(i, []) if i in deleted else [line]
        if not lines:
            continue
        if paint != last_paint:
            output.append('usemtl '+paint)
            last_paint = paint
        output.extend(lines)
        after_count += len(lines)
    target = OUT / 'stage' / Path(resource).name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('\n'.join(output)+'\n')
    return {
        'path': resource, 'source': target.relative_to(ROOT).as_posix(),
        'before_sha256': digest(source), 'sha256': digest(target),
        'triangles_before': len(faces), 'triangles_after': after_count,
        'original_wall_triangles_matched': matched,
        'hidden_surface_removed_m2': removed_area * .0254**2,
        'other_triangles_retained': len(faces)-len(deleted),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wall = B.Model()
    B.town_walls(wall, trim_buried=False)
    before_boxes = repr(wall.boxes)
    before_hulls = repr(wall.hulls)
    original = {paint: list(faces) for paint, faces in wall.polygons.items()}
    W.trim_model(wall, {})
    if repr(wall.boxes) != before_boxes or repr(wall.hulls) != before_hulls:
        raise ValueError('Wall collision changed')
    # Every outward west face must remain, including the retaining wall below
    # street level; the terrain drops away on that side of town.
    for paint, faces in original.items():
        for points, normal in faces:
            outside = (np.allclose([p[0] for p in points], -2380) and normal[0] < -.9
                       or np.allclose([p[1] for p in points], -1466) and normal[1] < -.9
                       or np.allclose([p[1] for p in points], 1800) and normal[1] > .9)
            if outside:
                if not any(len(p) == len(points) and np.allclose(p, points) for p, _ in wall.polygons[paint]):
                    raise ValueError('Exterior retaining face changed')
    raw = B.Model()
    B.town_walls(raw, trim_buried=False)
    files = [stage_half('west', False, raw), stage_half('east', True, raw)]
    protected = {}
    for name in ('west', 'east'):
        for path in sorted((ROOT / 'Assets/models/maps/belltower').glob(f'belltower_{name}*')):
            if path.suffix == '.vmdl' or '_hulls_' in path.name:
                protected[path.relative_to(ROOT / 'Assets').as_posix()] = digest(path)
    result = {'revision': 'wall-v2', 'files': files, 'protected_sha256': protected,
              'collision_unchanged': True, 'exterior_retaining_faces_unchanged': True,
              'overlap_below_floor_inches': 2,
              'hidden_surface_removed_m2': sum(f['hidden_surface_removed_m2'] for f in files),
              'triangles_before': sum(f['triangles_before'] for f in files),
              'triangles_after': sum(f['triangles_after'] for f in files)}
    (OUT / 'geometry-manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('protected_sha256', 'files')}, indent=2))


if __name__ == '__main__':
    main()
