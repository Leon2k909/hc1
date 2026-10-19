"""Stage a separate firewood construction trial without changing the live gardens.

The original ImageGen albedos and alpha stay byte-for-byte unchanged. Bark follows
the curved hull; split faces use lengthwise fibres and caps use annual rings. This is
an offline visual candidate, not a native import or an accepted map revision.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

import belltower_furniture as F
import belltower_gardens as G
from map_kit import Model, normalise, write_obj

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / 'Sources/Belltower/generated'
OUT = ROOT / 'output/belltower/quality/firewood-v1-studio'
BARK = 'firewood_bark_trial'
CUT = 'firewood_cut_trial'
SPLIT = 'firewood_split_trial'
TILE = 31.5  # About 80 cm around the original bark scan.


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atlas_regions():
    """Measure safe sampling circles; never rewrite the image or its alpha."""
    path = GENERATED / 'firewood-cuts-v1.png'
    image = Image.open(path)
    assert image.mode == 'RGBA'
    alpha = np.asarray(image.getchannel('A'))
    height, width = alpha.shape
    regions = []
    for row in range(2):
        for col in range(2):
            x0, x1 = col * width // 2, (col + 1) * width // 2
            y0, y1 = row * height // 2, (row + 1) * height // 2
            mask = alpha[y0:y1, x0:x1] >= 250
            ys, xs = np.where(mask)
            cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
            radius = float(ndimage.distance_transform_edt(mask)[round(cy), round(cx)]) - 3
            assert radius > min(mask.shape) * .35, 'Atlas face has insufficient opaque coverage'
            regions.append({'centre': [(cx + x0) / width, 1 - (cy + y0) / height],
                            'radius': [radius / width, radius / height]})
    return regions


def _surface(profile, x, upper):
    heights = []
    for a, b in zip(profile, profile[1:] + profile[:1]):
        if min(a[0], b[0]) - 1e-7 <= x <= max(a[0], b[0]) + 1e-7 and abs(b[0] - a[0]) > 1e-7:
            t = (x - a[0]) / (b[0] - a[0])
            heights.append(a[1] + t * (b[1] - a[1]))
    return (max if upper else min)(heights)


def woodpile(model, e0, e1, n0, n1, z, height=40, regions=None,
             material_dir='materials/belltower/firewood-trial-v1'):
    """Rounded bark, broad split surfaces and coherent end-grain placement."""
    regions = regions or atlas_regions()
    model.material_overrides.update({BARK: f'{material_dir}/bark.vmat',
                                     CUT: f'{material_dir}/cuts.vmat',
                                     SPLIT: f'{material_dir}/split.vmat'})
    model.tile_overrides.update({BARK: TILE, CUT: 1, SPLIT: TILE})
    rng = np.random.default_rng(G._seed(e0, n0, z))
    radius = min(height / 7.4, (e1 - e0) / 18.5)
    spacing = (e1 - e0 - 2 * radius) / 8
    previous, records = [], []
    for row in range(4):
        current = []
        for k in range(9 if row % 2 == 0 else 8):
            e = e0 + radius + (row % 2) * spacing * .5 + k * spacing
            angle = rng.uniform(0, math.tau)
            split = rng.random() > .22
            span = rng.uniform(math.radians(215), math.radians(300)) if split else math.tau
            angles = np.linspace(angle, angle + span, 24, endpoint=split)
            # Low-frequency irregular growth remains convex after the hull pass.
            radial = 1 + .018 * np.sin(angles * 3 + rng.uniform(0, math.tau))
            raw = np.column_stack((np.cos(angles) * radial, np.sin(angles) * radial))
            raw[:, 1] *= rng.uniform(.92, 1.0)
            raw = raw[ConvexHull(raw).vertices]
            raw /= np.linalg.norm(raw, axis=1).max()
            log_radius = radius * rng.uniform(.86, 1.0)
            profile = (raw * log_radius).tolist()
            footprint = [(e + x, h) for x, h in profile]
            centre_z = z - min(p[1] for p in profile) + .04
            for support in previous:
                lo = max(min(p[0] for p in footprint), min(p[0] for p in support))
                hi = min(max(p[0] for p in footprint), max(p[0] for p in support))
                if hi <= lo:
                    continue
                xs = [lo, hi] + [p[0] for p in footprint + support if lo < p[0] < hi]
                centre_z = max(centre_z, max(_surface(support, x, True) - _surface(footprint, x, False) for x in xs) + .02)
            current.append([(e + x, centre_z + h) for x, h in profile])
            start, end = n0 + rng.uniform(.15, 2.8), n1 - rng.uniform(.15, 2.8)
            middle = (start + end) * .5
            point_count = len(profile)
            edges = [(np.asarray(profile[i]), np.asarray(profile[(i + 1) % point_count])) for i in range(point_count)]
            split_edges = [bool(split and np.linalg.norm(b - a) > log_radius * .65) for a, b in edges]
            face_normals = [normalise((b[1] - a[1], 0, a[0] - b[0])) for a, b in edges]
            smooth = []
            for i in range(point_count):
                smooth.append(normalise(face_normals[i - 1] + face_normals[i]) if not split_edges[i - 1] and not split_edges[i]
                              else face_normals[i] if not split_edges[i] else face_normals[i - 1])
            distances = np.concatenate(([0.0], np.cumsum([np.linalg.norm(b - a) for a, b in edges])))
            offset = rng.random(2)
            vertical_offset = .01 + offset[1] * max(0, .98 - (end - start) / TILE)

            def at(point, n, scale=1.0):
                return np.array((e + point[0] * scale, n, centre_z + point[1] * scale))

            for i, (a, b) in enumerate(edges):
                normal = face_normals[i]
                paint = SPLIT if split_edges[i] else BARK
                u0, u1 = offset[0] + distances[i] / TILE, offset[0] + distances[i + 1] / TILE
                if split_edges[i]:
                    width = np.linalg.norm(b - a) / TILE
                    u0 = offset[0] * (1 - width)
                    u1 = u0 + width
                for na, nb, sa, sb in ((start + .15, middle, 1.0, .985), (middle, end - .15, .985, 1.0)):
                    va, vb = vertical_offset + (na - start) / TILE, vertical_offset + (nb - start) / TILE
                    uv = [(u0, va), (u1, va), (u1, vb), (u0, vb)]
                    normals = None if split_edges[i] else [smooth[i], smooth[(i + 1) % point_count], smooth[(i + 1) % point_count], smooth[i]]
                    F.face(model, paint, [at(a, na, sa), at(b, na, sa), at(b, nb, sb), at(a, nb, sb)], normal, uv, normals)
                for n, inner, sign in ((start, start + .15, -1), (end, end - .15, 1)):
                    vi, vn = vertical_offset + (inner - start) / TILE, vertical_offset + (n - start) / TILE
                    uv = [(u0, vi), (u1, vi), (u1, vn), (u0, vn)]
                    F.face(model, paint, [at(a, inner), at(b, inner), at(b, n, .978), at(a, n, .978)],
                           normal + np.array((0, sign * log_radius, 0)), uv)
            atlas_index = int(rng.integers(0, len(regions)))
            region = regions[atlas_index]
            rotation = rng.uniform(0, math.tau)
            c, s = math.cos(rotation), math.sin(rotation)
            uv = [(region['centre'][0] + (p[0] * c - p[1] * s) / log_radius * region['radius'][0],
                   region['centre'][1] + (p[0] * s + p[1] * c) / log_radius * region['radius'][1]) for p in profile]
            for n, normal in ((start, (0, -1, 0)), (end, (0, 1, 0))):
                F.face(model, CUT, [at(p, n, .978) for p in profile], normal, uv)
            records.append({'row': row, 'column': k, 'profile_vertices': point_count, 'split_faces': sum(split_edges),
                            'atlas': atlas_index, 'centre': [e, centre_z], 'radius': log_radius})
        previous = current
    return records


def _studio_material(path, source):
    # Absolute source paths are only for this offline renderer, never a live asset.
    path.write_text('"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                    '    g_flMetalness "0"\n    g_vColorTint "[1 1 1 1]"\n'
                    f'    TextureColor "{source.as_posix()}"\n}}\n', encoding='utf-8')


def stage():
    import belltower_map as B
    import building_textures as BT
    assert OUT.resolve().is_relative_to((ROOT / 'output/belltower/quality').resolve())
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = [Path(__file__), ROOT / 'Tools/belltower_gardens.py', ROOT / 'Tools/belltower_furniture.py',
                    ROOT / 'Tools/map_kit.py']
    source_paths += [GENERATED / f'firewood-{name}-v1.{suffix}' for name in ('cuts', 'bark', 'split') for suffix in ('png', 'json')]
    sources = {p.relative_to(ROOT).as_posix(): digest(p) for p in source_paths}
    assert sources['Tools/belltower_gardens.py'] == '5bbf7dc306f955e4cd81f6369b40275f4a3c7559d34e5624352a095d37a72b8b', 'Review the pending garden v3 before changing this baseline'
    regions = atlas_regions()
    material_dir = OUT / 'studio-materials'
    material_dir.mkdir(exist_ok=True)
    _studio_material(material_dir / 'bark.vmat', GENERATED / 'firewood-bark-v1.png')
    _studio_material(material_dir / 'cuts.vmat', GENERATED / 'firewood-cuts-v1.png')
    _studio_material(material_dir / 'split.vmat', GENERATED / 'firewood-split-v1.png')
    before, after = Model(), Model()
    G.woodpile(before, -50, 50, -15, 15, 0)
    logs = woodpile(after, -50, 50, -15, 15, 0, regions=regions)
    after.material_overrides[BARK] = str(material_dir / 'bark.vmat')
    after.material_overrides[CUT] = str(material_dir / 'cuts.vmat')
    after.material_overrides[SPLIT] = str(material_dir / 'split.vmat')
    records, counts = [], {}
    for name, model in (('firewood-before', before), ('firewood-after', after)):
        B.Detail.configure(model)
        points = np.asarray([point for faces in model.polygons.values() for face, _ in faces for point in face])
        assert not model.boxes and not model.hulls
        assert np.all(points.min(axis=0) >= (-50.001, -15.001, -.001))
        assert np.all(points.max(axis=0) <= (50.001, 15.001, 40.001))
        write_obj(OUT / f'{name}.obj', model, 'belltower_west')
        counts[name] = {'triangles': model.triangle_count(), 'bounds': [points.min(axis=0).tolist(), points.max(axis=0).tolist()]}
        records.append({'name': name, 'triangles': model.triangle_count(), 'review_bounds': [[-50, -15, 0], [50, 15, 40]],
                        'materials': {paint: model.material_overrides.get(paint, BT.material_path(paint)) for paint in model.polygons}})
    (OUT / 'models.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    report = {'state': 'offline candidate; native integration and visual review pending', 'source_sha256': sources,
              'atlas_regions': regions, 'logs': logs, 'models': counts,
              'live_garden_generator_unchanged': digest(ROOT / 'Tools/belltower_gardens.py') == sources['Tools/belltower_gardens.py'],
              'live_assets_written': False, 'collision_authored': False,
              'limitations': ['No surface normal map yet for the generated albedos.', 'Native appearance and runtime cost are unverified.']}
    (OUT / 'trial.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'directory': str(OUT), 'models': counts, 'logs': len(logs), 'split_logs': sum(x['split_faces'] > 0 for x in logs)}))


if __name__ == '__main__':
    stage()
