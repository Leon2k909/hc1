"""Offline candidate for Lowtide's cast-iron window construction.

The production window writer is deliberately unchanged until native review.
This module supplies its eventual frame implementation and stages exact visual
face replacements against the current OBJ files. Panes, rooms, masonry,
collision, materials and scene files are never written by this command.

    rtk python Tools/lowtide_window_construction.py --stage <outside-Assets-dir>
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import map_kit as K

REVISION = "cast-frame-v2"
DETAIL_SILL_MAX = 320.0
FRAME_WIDTH = 2.6
BAR_HALF = .75
FRAME_PROFILE = ((0., -6.12), (0., -4.55), (.24, -4.25),
                 (1.55, -4.25), (FRAME_WIDTH, -5.94), (FRAME_WIDTH, -6.12))
BAR_PROFILE = ((-.75, -5.97), (-.75, -5.18), (-.48, -4.62),
               (.48, -4.62), (.75, -5.18), (.75, -5.97))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(L):
    """Capture layout in memory; never invoke the map's file-writing build."""
    records = {}
    original = L.window
    try:
        for name, builder in (("lowtide_east", L.half), ("lowtide_backdrop", L.backdrop)):
            rows = []
            def record(model, wall, opening, style, pane=None, glass=None):
                rows.append(dict(axis=wall.axis, run=wall.run, across=wall.across,
                                 wall_z=wall.z, outward=wall.outward,
                                 opening=[opening.r0, opening.r1, opening.z0, opening.z1, opening.kind],
                                 style=vars(style), transparent=glass is not None))
            L.window = record
            builder()
            records[name] = rows
    finally:
        L.window = original
    return records


def unpack(row, L):
    wall = K.Wall(row["axis"], row["run"], row["across"], row["wall_z"], row["outward"])
    opening = K.Opening(*row["opening"])
    return wall, opening, L.Style(**row["style"])


def local_point(wall, r, z, depth):
    d, sign = wall.outer()
    return wall.point(r, d + sign * depth, z)


def contour(o, inset, steps):
    if not o.arched:
        return [(o.r0 + inset, o.z0 + inset), (o.r1 - inset, o.z0 + inset),
                (o.r1 - inset, o.z1 - inset), (o.r0 + inset, o.z1 - inset)]
    return [(o.r0 + inset, o.z0 + inset), (o.r1 - inset, o.z0 + inset)] + [
        ((o.r0 + o.r1) * .5 + (o.radius - inset) * math.cos(t),
         o.spring + (o.radius - inset) * math.sin(t))
        for t in np.linspace(0, math.pi, steps + 1)]


def surround(m, L, wall, o, paint, *, head_only=False):
    """A shaped metal section, including the missing curved head of the frame.

    Detailed surrounds have a narrow cast shoulder and a sloping glazing bead.
    Upper windows receive only a simple head, keeping distant geometry modest.
    The outside edge follows the existing opening; no hole is enlarged.
    """
    steps = 20 if not head_only else 10
    profile = FRAME_PROFILE if not head_only else ((0., -6.12), (0., -4.4),
                                                  (2.6, -4.4), (2.6, -6.12))
    loops = [contour(o, inset, steps) for inset, depth in profile]
    indices = range(2, len(loops[0]) - 1) if head_only else range(len(loops[0]))
    out = L.wall_out(wall)[2]
    for section, (inset_a, depth_a) in enumerate(profile):
        # Outer faces are buried in the masonry reveal. Sealed upper windows
        # also hide the back of the head behind their opaque pane.
        if section == 0 or (head_only and section == len(profile) - 1):
            continue
        following = (section + 1) % len(profile)
        inset_b, depth_b = profile[following]
        for j in indices:
            k = (j + 1) % len(loops[0])
            a, b = loops[section], loops[following]
            points = [local_point(wall, *a[j], depth_a), local_point(wall, *a[k], depth_a),
                      local_point(wall, *b[k], depth_b), local_point(wall, *b[j], depth_b)]
            # The inside direction of this segment in the wall's plane.
            r, z = np.subtract(a[k], a[j])
            inward = wall.point(-z, 0, r) - wall.point(0, 0, 0)
            inward /= np.linalg.norm(inward)
            towards = out * (inset_b - inset_a) - inward * (depth_b - depth_a)
            # Smooth only the arched spans. Sharp straight/mitered corners retain
            # face normals so a broad frame face never gets rounded shading.
            if 2 <= j < len(a) - 1 and o.arched:
                normals = []
                for index in (j, k, k, j):
                    theta = math.pi * (index - 2) / steps
                    radial = wall.point(-math.cos(theta), 0, -math.sin(theta)) - wall.point(0, 0, 0)
                    n = out * (inset_b - inset_a) - radial * (depth_b - depth_a)
                    normals.append(n / np.linalg.norm(n))
                normal = np.cross(points[1] - points[0], points[2] - points[0])
                if np.dot(normal, towards) < 0:
                    points = points[:1] + points[:0:-1]
                    normals = normals[:1] + normals[:0:-1]
                m.polygon(paint, points, normal=towards, normals=normals)
            else:
                L.card(m, paint, points, towards)


def bar(m, L, wall, centre, start, finish, paint, *, vertical, cap=False):
    """Bevelled glazing bar; horizontal segments terminate at vertical bars.

    Unlike crossed boxes, the two front faces do not occupy the same plane at
    intersections. Ends under the surround are omitted rather than overdrawn.
    """
    def point(along, offset, depth):
        r, z = (centre + offset, along) if vertical else (along, centre + offset)
        return local_point(wall, r, z, depth)
    rings = [[point(t, width, depth) for width, depth in BAR_PROFILE] for t in (start, finish)]
    middle = np.mean(rings, axis=(0, 1))
    for j in range(len(BAR_PROFILE)):
        k = (j + 1) % len(BAR_PROFILE)
        points = [rings[0][j], rings[1][j], rings[1][k], rings[0][k]]
        L.card(m, paint, points, np.mean(points, axis=0) - middle)
    if cap:
        for ring in rings:
            L.card(m, paint, ring, np.mean(ring, axis=0) - middle)


def frame(m, L, wall, o, style):
    """Complete frame for reachable windows, simple arch head for upper ones."""
    if o.z0 > DETAIL_SILL_MAX:
        if o.arched:
            surround(m, L, wall, o, style.frame, head_only=True)
        return
    surround(m, L, wall, o, style.frame)
    width = o.r1 - o.r0
    uprights = [o.r0 + width * k / 3 for k in (1, 2)]
    for r in uprights:
        end = o.z1 - 1.35
        if o.arched:
            end = o.spring + math.sqrt(max(0, (o.radius - 1.35) ** 2 - (r - (o.r0 + o.r1) / 2) ** 2))
        bar(m, L, wall, r, o.z0 + 1.6, end, style.frame, vertical=True)
    top = o.spring if o.arched else o.z1
    levels = list(np.arange(o.z0 + 22, top - 4, 20))
    if o.arched:
        levels.append(top)
    # Butt the flat front exactly against the upright's shoulder. The bevel
    # ends lie within its solid section; no open gap or coplanar overlap.
    shoulder = .48
    spans = [(o.r0 + 1.6, uprights[0] - shoulder),
             (uprights[0] + shoulder, uprights[1] - shoulder),
             (uprights[1] + shoulder, o.r1 - 1.6)]
    for z in levels:
        for a, b in spans:
            bar(m, L, wall, z, a, b, style.frame, vertical=False)


def geometry(rows, L):
    removed, replacement = K.Model(), K.Model()
    for row in rows:
        wall, o, style = unpack(row, L)
        if o.z0 <= DETAIL_SILL_MAX:
            old = K.Model()
            L.window(old, wall, o, style)
            # Only frame-painted polygons are eligible for removal. Panes and
            # the arch/sill stay in their existing OBJ records, UVs and normals.
            for points, normal in old.polygons[style.frame]:
                removed.polygon(style.frame, points, normal)
        frame(replacement, L, wall, o, style)
    L.configure(removed)
    L.configure(replacement)
    assert not removed.boxes and not replacement.boxes
    assert not removed.hulls and not replacement.hulls
    return removed, replacement


def face_keys(text, *, attributes=False):
    positions, uvs, normals = [], [], []
    paint, result = None, Counter()
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v": positions.append(tuple(map(float, fields[1:])))
        elif fields[0] == "vt": uvs.append(tuple(map(float, fields[1:])))
        elif fields[0] == "vn": normals.append(tuple(map(float, fields[1:])))
        elif fields[0] == "usemtl": paint = fields[1]
        elif fields[0] == "f":
            refs = [tuple(int(x) - 1 for x in item.split("/")) for item in fields[1:]]
            points = tuple((positions[v], uvs[t], normals[n]) if attributes else positions[v] for v, t, n in refs)
            result[(paint, points)] += 1
    return result


def replace_faces(original, old, new):
    """Remove exact old triangles, keeping all unrelated records verbatim."""
    remove = face_keys(old)
    positions, kept, removed_lines = [], [], []
    counts, paint = Counter(), None
    for line in original.splitlines():
        fields = line.split()
        if fields and fields[0] in ("v", "vt", "vn"):
            counts[fields[0]] += 1
            if fields[0] == "v": positions.append(tuple(map(float, fields[1:])))
        elif fields and fields[0] == "usemtl": paint = fields[1]
        elif fields and fields[0] == "f":
            key = (paint, tuple(positions[int(item.split('/')[0]) - 1] for item in fields[1:]))
            if remove[key]:
                remove[key] -= 1
                removed_lines.append(line)
                continue
        kept.append(line)
    missing = +remove
    if missing:
        raise ValueError(f"{sum(missing.values())} expected frame faces do not match the live source")
    addition = []
    for line in new.splitlines():
        if line.startswith(("v ", "vt ", "vn ", "usemtl ")):
            addition.append(line)
        elif line.startswith("f "):
            entries = ["/".join(str(int(v) + counts[k]) for v, k in zip(point.split('/'), ('v', 'vt', 'vn')))
                       for point in line.split()[1:]]
            addition.append('f ' + ' '.join(entries))
    return '\n'.join(kept + [f'# {REVISION}'] + addition) + '\n', len(removed_lines)


def validate_model(model):
    for paint, faces in model.polygons.items():
        for index, (points, normal) in enumerate(faces):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            for k in range(1, len(points) - 1):
                cross = np.cross(points[k] - points[0], points[k+1] - points[0])
                assert np.linalg.norm(cross) > 1e-7, (paint, index, "degenerate")
                assert np.dot(cross, normal) > 0, (paint, index, "winding")
            for n in model.polygon_normals.get((paint, index), []):
                assert abs(np.linalg.norm(n) - 1) < 1e-7
                assert np.dot(n, normal) > 0


def stage(out):
    import lowtide_map as L
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve()), "Offline staging must be outside Assets"
    out.mkdir(parents=True, exist_ok=True)
    cache = out / 'layout.json'
    source_hash = sha(Path(L.__file__))
    if cache.exists():
        cached = json.loads(cache.read_text())
        assert cached['map_source_sha256'] == source_hash, 'Layout changed; use a new stage directory'
        records = cached['models']
    else:
        records = collect(L)
        cache.write_text(json.dumps({'map_source_sha256': source_hash, 'models': records}, indent=2) + '\n')
    protected = {}
    for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide'):
        for path in (K.ROOT / folder).rglob('*'):
            if path.is_file() and not path.name.endswith('_c'):
                protected[path.relative_to(K.ROOT).as_posix()] = sha(path)
    original, candidate = geometry(records['lowtide_east'], L)
    pairs = {'lowtide_east': (original, candidate),
             'lowtide_west': (original.mirrored(L.WEST_PAINTS), candidate.mirrored(L.WEST_PAINTS)),
             'lowtide_backdrop': geometry(records['lowtide_backdrop'], L)}
    manifest = {'revision': REVISION, 'status': 'offline_candidate_not_imported', 'models': {},
                'protected': protected, 'changes': {}, 'layout': 'layout.json',
                'scene_changed': False, 'materials_changed': False, 'collision_changed': False}
    for name, (old, new) in pairs.items():
        validate_model(new)
        L.configure(old)
        L.configure(new)
        for label, model in (('old', old), ('new', new)):
            K.write_obj(out / f'{name}-{label}.obj', model, name)
        live = L.OUT_DIR / f'{name}.obj'
        before = out / 'before' / live.name
        before.parent.mkdir(exist_ok=True)
        data = live.read_bytes()
        if before.exists(): assert before.read_bytes() == data, 'Live model changed since offline staging'
        else: before.write_bytes(data)
        old_text = (out / f'{name}-old.obj').read_text()
        new_text = (out / f'{name}-new.obj').read_text()
        original_text = data.decode()
        updated, removed = replace_faces(original_text, old_text, new_text)
        target = out / 'stage/models/maps/lowtide' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(updated.encode())
        expected = face_keys(original_text) - face_keys(old_text) + face_keys(new_text)
        assert face_keys(updated) == expected, 'Unexpected geometry delta'
        # Attribute comparison also verifies the pane mapping and all normals
        # on preserved triangles, independent of appended OBJ index offsets.
        full_original = face_keys(original_text, attributes=True)
        full_updated = face_keys(updated, attributes=True)
        non_frame = lambda c: Counter({k: v for k, v in c.items() if k[0] not in ('lt_frame_green', 'lt_frame_cream')})
        assert non_frame(full_original) == non_frame(full_updated), 'Non-frame attributes changed'
        for paint in new.polygons:
            assert f'from = "{paint}.vmat"' in live.with_suffix('.vmdl').read_text(), paint
        rows = records['lowtide_east' if name == 'lowtide_west' else name]
        manifest['models'][name] = dict(windows=len(rows), detailed=sum(r['opening'][2] <= DETAIL_SILL_MAX for r in rows),
                                      removed_triangles=removed, added_triangles=new.triangle_count(),
                                      preserved_triangles=sum(full_original.values()) - removed)
        manifest['changes'][live.relative_to(K.ASSETS).as_posix()] = {'before': sha(live), 'after': sha(target)}
    assert all(sha(K.ROOT / path) == value for path, value in protected.items()), 'Offline work touched live assets'
    manifest['delta_triangles'] = sum(m['added_triangles'] - m['removed_triangles'] for m in manifest['models'].values())
    manifest['generator_sha256'] = sha(Path(__file__))
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ('status', 'models', 'delta_triangles')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
